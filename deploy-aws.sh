#!/bin/bash
set -e

echo "========================================="
echo "AWS Greengrass Edge LLM Deployment"
echo "========================================="

# Configuration
export AWS_PROFILE="${AWS_PROFILE:-Rhodes}"
export AWS_REGION="${AWS_REGION:-eu-central-1}"
PROJECT_NAME="edge-llm-greengrass"
COMPONENT_VERSION="1.0.0"

echo "Using AWS Profile: $AWS_PROFILE"
echo "Region: $AWS_REGION"
echo ""

# Step 1: Deploy Infrastructure
echo "Step 1: Deploying infrastructure with Terraform..."
cd infrastructure

terraform init
terraform plan -var="aws_region=$AWS_REGION" -var="project_name=$PROJECT_NAME"

echo "Do you want to apply these changes? (yes/no)"
read -r response
if [[ "$response" != "yes" ]]; then
    echo "Deployment cancelled."
    exit 1
fi

terraform apply -auto-approve -var="aws_region=$AWS_REGION" -var="project_name=$PROJECT_NAME"

# Get outputs
EC2_PUBLIC_IP=$(terraform output -raw ec2_public_ip)
EC2_INSTANCE_ID=$(terraform output -raw ec2_instance_id)
S3_BUCKET=$(terraform output -raw s3_bucket_name)
IOT_THING_NAME=$(terraform output -raw iot_thing_name)
IOT_THING_GROUP_ARN=$(terraform output -raw iot_thing_group_arn)
ROLE_ALIAS=$(terraform output -raw token_exchange_role_alias)

cd ..

echo ""
echo "Infrastructure deployed:"
echo "  EC2 Public IP: $EC2_PUBLIC_IP"
echo "  EC2 Instance ID: $EC2_INSTANCE_ID"
echo "  S3 Bucket: $S3_BUCKET"
echo "  IoT Thing: $IOT_THING_NAME"
echo ""

# Step 2: Wait for EC2 to be ready
echo "Step 2: Waiting for EC2 instance to be ready..."
aws ec2 wait instance-status-ok --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION"

# Wait for user data to complete
echo "Waiting for user data script to complete..."
while ! aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["test -f /tmp/greengrass-ready && echo ready || echo not-ready"]' \
    --region "$AWS_REGION" \
    --output text --query "Command.CommandId" 2>/dev/null; do
    echo "Waiting for instance to be accessible..."
    sleep 10
done

sleep 30  # Give extra time for everything to settle

echo "EC2 instance is ready!"
echo ""

# Step 3: Upload component artifacts to S3
echo "Step 3: Uploading component artifacts to S3..."

# Upload ChatBot UI component
echo "Uploading ChatBot UI component..."
aws s3 cp components/chatbot-ui/simple_chatbot.py "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$COMPONENT_VERSION/" --region "$AWS_REGION"
aws s3 cp components/chatbot-ui/requirements.txt "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$COMPONENT_VERSION/" --region "$AWS_REGION"

# Upload Sensor Simulator component
echo "Uploading Sensor Simulator component..."
aws s3 cp components/sensor-simulator/simple_sensor_gen.py "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$COMPONENT_VERSION/" --region "$AWS_REGION"
aws s3 cp components/sensor-simulator/requirements.txt "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$COMPONENT_VERSION/" --region "$AWS_REGION"

# Upload Grafana dashboard
echo "Uploading Grafana dashboard configuration..."
aws s3 cp grafana-dashboards/edge-llm-dashboard.json "s3://$S3_BUCKET/grafana-dashboards/" --region "$AWS_REGION"

echo "Component artifacts uploaded to S3!"
echo ""

# Step 4: Register components in AWS IoT Greengrass
echo "Step 4: Registering components in AWS IoT Greengrass..."

# Create ChatBot UI component recipe
cat > /tmp/chatbot-recipe.json <<EOF
{
  "RecipeFormatVersion": "2020-01-25",
  "ComponentName": "com.edge.llm.ChatBotUI",
  "ComponentVersion": "$COMPONENT_VERSION",
  "ComponentDescription": "Interactive ChatBot web interface with TinyLlama LLM",
  "ComponentPublisher": "EdgeLLM",
  "ComponentConfiguration": {
    "DefaultConfiguration": {
      "webPort": 8080,
      "chatHistoryLimit": 50,
      "enableDebugMode": true
    }
  },
  "Manifests": [
    {
      "Platform": {
        "os": "linux"
      },
      "Lifecycle": {
        "Install": "pip3 install -r {artifacts:path}/requirements.txt --index-url https://download.pytorch.org/whl/cu121",
        "Run": "python3 -u {artifacts:path}/simple_chatbot.py"
      },
      "Artifacts": [
        {
          "URI": "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$COMPONENT_VERSION/simple_chatbot.py"
        },
        {
          "URI": "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$COMPONENT_VERSION/requirements.txt"
        }
      ]
    }
  ]
}
EOF

# Create Sensor Simulator component recipe
cat > /tmp/sensor-recipe.json <<EOF
{
  "RecipeFormatVersion": "2020-01-25",
  "ComponentName": "com.edge.llm.SensorSimulator",
  "ComponentVersion": "$COMPONENT_VERSION",
  "ComponentDescription": "Industrial sensor data simulator",
  "ComponentPublisher": "EdgeLLM",
  "ComponentConfiguration": {
    "DefaultConfiguration": {
      "sensorCount": 5,
      "samplingIntervalMs": 5000,
      "anomalyProbability": 0.05,
      "sensors": {
        "temperature": {
          "min": 20,
          "max": 80,
          "unit": "celsius"
        },
        "pressure": {
          "min": 100,
          "max": 200,
          "unit": "kPa"
        },
        "vibration": {
          "min": 0,
          "max": 10,
          "unit": "mm/s"
        }
      }
    }
  },
  "Manifests": [
    {
      "Platform": {
        "os": "linux"
      },
      "Lifecycle": {
        "Install": "pip3 install -r {artifacts:path}/requirements.txt",
        "Run": "python3 -u {artifacts:path}/simple_sensor_gen.py"
      },
      "Artifacts": [
        {
          "URI": "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$COMPONENT_VERSION/simple_sensor_gen.py"
        },
        {
          "URI": "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$COMPONENT_VERSION/requirements.txt"
        }
      ]
    }
  ]
}
EOF

# Create components in Greengrass
echo "Creating ChatBot UI component..."
aws greengrassv2 create-component-version \
    --inline-recipe fileb:///tmp/chatbot-recipe.json \
    --region "$AWS_REGION" || echo "Component might already exist, continuing..."

echo "Creating Sensor Simulator component..."
aws greengrassv2 create-component-version \
    --inline-recipe fileb:///tmp/sensor-recipe.json \
    --region "$AWS_REGION" || echo "Component might already exist, continuing..."

echo "Components registered!"
echo ""

# Step 5: Install Greengrass on EC2
echo "Step 5: Installing Greengrass Core on EC2..."

# Create installation script
cat > /tmp/install-greengrass.sh <<'SCRIPT'
#!/bin/bash
set -e

# Wait for NVIDIA drivers to be ready
nvidia-smi || echo "GPU not ready yet"

# Install Greengrass
cd /tmp/GreengrassInstaller

sudo -E java -Droot="/greengrass/v2" \
    -Dlog.store=FILE \
    -jar ./lib/Greengrass.jar \
    --aws-region $AWS_REGION \
    --thing-name $IOT_THING_NAME \
    --thing-group-name edge-llm-greengrass-group \
    --tes-role-alias-name $ROLE_ALIAS \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true \
    --deploy-dev-tools true

# Start Greengrass
sudo systemctl start greengrass
sudo systemctl enable greengrass

# Configure Grafana dashboard
echo "Configuring Grafana dashboard..."
aws s3 cp s3://$S3_BUCKET/grafana-dashboards/edge-llm-dashboard.json /tmp/dashboard.json
cp /tmp/dashboard.json /etc/grafana/provisioning/dashboards/

# Create dashboard provisioning config
cat > /etc/grafana/provisioning/dashboards/edge-llm.yaml <<'DASHBOARD_CONFIG'
apiVersion: 1

providers:
  - name: 'Edge LLM IoT'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
DASHBOARD_CONFIG

systemctl restart grafana-server

echo "Greengrass installed successfully!"
SCRIPT

# Copy and run installation script on EC2
echo "Running Greengrass installation on EC2..."
aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[
        'export AWS_REGION=$AWS_REGION',
        'export IOT_THING_NAME=$IOT_THING_NAME',
        'export ROLE_ALIAS=$ROLE_ALIAS',
        '$(cat /tmp/install-greengrass.sh)'
    ]" \
    --region "$AWS_REGION" \
    --output text

echo "Waiting for Greengrass installation to complete..."
sleep 60

# Step 6: Create Greengrass deployment
echo "Step 6: Creating Greengrass deployment..."

cat > /tmp/deployment.json <<EOF
{
  "targetArn": "$IOT_THING_GROUP_ARN",
  "deploymentName": "edge-llm-full-deployment",
  "components": {
    "aws.greengrass.Cli": {
      "componentVersion": "2.12.6"
    },
    "aws.greengrass.Nucleus": {
      "componentVersion": "2.12.6"
    },
    "com.edge.llm.ChatBotUI": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{\"webPort\": 8080}"
      }
    },
    "com.edge.llm.SensorSimulator": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{\"sensorCount\": 5, \"samplingIntervalMs\": 5000}"
      }
    }
  },
  "deploymentPolicies": {
    "failureHandlingPolicy": "ROLLBACK",
    "componentUpdatePolicy": {
      "timeoutInSeconds": 900,
      "action": "NOTIFY_COMPONENTS"
    }
  }
}
EOF

DEPLOYMENT_ID=$(aws greengrassv2 create-deployment \
    --cli-input-json file:///tmp/deployment.json \
    --region "$AWS_REGION" \
    --output text --query "deploymentId")

echo "Deployment created with ID: $DEPLOYMENT_ID"
echo ""

# Wait for deployment
echo "Waiting for deployment to complete..."
sleep 30

# Check deployment status
aws greengrassv2 get-deployment \
    --deployment-id "$DEPLOYMENT_ID" \
    --region "$AWS_REGION" \
    --query "deploymentStatus" \
    --output text

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Access your services at:"
echo "  ChatBot UI: http://$EC2_PUBLIC_IP:8080"
echo "  SSH Access: ssh ec2-user@$EC2_PUBLIC_IP"
echo ""
echo "Check component status:"
echo "  aws ssm send-command --instance-ids $EC2_INSTANCE_ID --document-name AWS-RunShellScript --parameters 'commands=[\"sudo /greengrass/v2/bin/greengrass-cli component list\"]' --region $AWS_REGION"
echo ""
echo "View logs:"
echo "  aws ssm send-command --instance-ids $EC2_INSTANCE_ID --document-name AWS-RunShellScript --parameters 'commands=[\"sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log\"]' --region $AWS_REGION"
echo ""