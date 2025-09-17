#!/bin/bash
set -e

echo "========================================="
echo "AWS Greengrass Edge LLM Deployment"
echo "========================================="

# Configuration
export AWS_PROFILE="${AWS_PROFILE:-Rhodes}"
export AWS_REGION="${AWS_REGION:-eu-central-1}"
PROJECT_NAME="edge-llm-greengrass"
IOT_THING_NAME="${IOT_THING_NAME:-EdgeLLMDemoAWS-$(date +%s)}"
CHATBOT_VERSION="1.0.8"
SENSOR_VERSION="1.0.1"

echo "Using AWS Profile: $AWS_PROFILE"
echo "Region: $AWS_REGION"
echo "IoT Thing Name: $IOT_THING_NAME"
echo ""

# Check if SSH key exists, create if not
if [ ! -f ~/.ssh/greengrass-key ]; then
    echo "SSH key not found. Generating SSH key pair for EC2 access..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/greengrass-key -C "greengrass-ec2-key" -N ""
    chmod 600 ~/.ssh/greengrass-key
    echo "SSH key generated at ~/.ssh/greengrass-key"
else
    echo "SSH key found at ~/.ssh/greengrass-key"
fi
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
ROLE_ALIAS=$(terraform output -raw token_exchange_role_alias)

# IoT Thing name will be created by Greengrass during provisioning
IOT_THING_GROUP_ARN="arn:aws:iot:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):thinggroup/edge-llm-greengrass-group"

cd ..

echo ""
echo "Infrastructure deployed:"
echo "  EC2 Public IP: $EC2_PUBLIC_IP"
echo "  EC2 Instance ID: $EC2_INSTANCE_ID"
echo "  S3 Bucket: $S3_BUCKET"
echo "  IoT Thing will be created by Greengrass: $IOT_THING_NAME"
echo ""

# Step 2: Wait for EC2 to be ready
echo "Step 2: Waiting for EC2 instance to be ready..."
aws ec2 wait instance-status-ok --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION"

# Wait for SSH to be accessible
echo "Waiting for SSH access to be ready..."
while ! ssh -i ~/.ssh/greengrass-key -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" "echo SSH Ready" 2>/dev/null; do
    echo "Waiting for SSH to be accessible..."
    sleep 10
done

# Wait for user data to complete
echo "Waiting for user data script to complete..."
while ! ssh -i ~/.ssh/greengrass-key -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" "test -f /tmp/greengrass-ready" 2>/dev/null; do
    echo "Waiting for instance setup to complete..."
    sleep 10
done

echo "EC2 instance is ready!"
echo ""

# Step 3: Upload component artifacts to S3
echo "Step 3: Uploading component artifacts to S3..."

# Upload ChatBot UI component
echo "Uploading ChatBot UI component..."
aws s3 cp components/chatbot-ui/simple_chatbot.py "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$CHATBOT_VERSION/" --region "$AWS_REGION"
aws s3 cp components/chatbot-ui/requirements.txt "s3://$S3_BUCKET/com.edge.llm.ChatBotUI/$CHATBOT_VERSION/" --region "$AWS_REGION"

# Upload Sensor Simulator component
echo "Uploading Sensor Simulator component..."
aws s3 cp components/sensor-simulator/simple_sensor_gen.py "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$SENSOR_VERSION/" --region "$AWS_REGION"
aws s3 cp components/sensor-simulator/requirements.txt "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$SENSOR_VERSION/" --region "$AWS_REGION"

# Upload shared utilities
echo "Uploading shared sensor utilities..."
aws s3 cp components/shared/sensor_utils.py "s3://$S3_BUCKET/com.edge.llm.SensorSimulator/$SENSOR_VERSION/" --region "$AWS_REGION"

# Upload Grafana component
echo "Uploading Grafana component..."
GRAFANA_VERSION="1.0.15"
cd components/grafana
tar -czf provisioning.tar.gz provisioning/
aws s3 cp provisioning.tar.gz "s3://$S3_BUCKET/com.edge.llm.Grafana/$GRAFANA_VERSION/" --region "$AWS_REGION"
rm provisioning.tar.gz
cd ../..

echo "Component artifacts uploaded to S3!"
echo ""

# Step 4: Register components in AWS IoT Greengrass
echo "Step 4: Registering components in AWS IoT Greengrass..."

# Update existing recipe files with correct S3 URIs
echo "Updating ChatBot UI recipe with S3 URLs..."
sed "s|s3://[^/]*/|s3://$S3_BUCKET/|g" components/chatbot-ui/recipe.json > /tmp/chatbot-recipe.json

echo "Updating Sensor Simulator recipe with S3 URLs..."
sed "s|s3://[^/]*/|s3://$S3_BUCKET/|g" components/sensor-simulator/recipe.json > /tmp/sensor-recipe.json

echo "Preparing InfluxDB recipe..."
cp components/influxdb/recipe.json /tmp/influxdb-recipe.json

echo "Updating Grafana recipe with S3 URLs..."
sed "s|s3://[^/]*/|s3://$S3_BUCKET/|g" components/grafana/recipe.json > /tmp/grafana-recipe.json

# Create components in Greengrass using existing recipe files
echo "Creating InfluxDB component..."
aws greengrassv2 create-component-version \
    --inline-recipe fileb:///tmp/influxdb-recipe.json \
    --region "$AWS_REGION" || echo "Component might already exist, continuing..."

echo "Creating Grafana component..."
aws greengrassv2 create-component-version \
    --inline-recipe fileb:///tmp/grafana-recipe.json \
    --region "$AWS_REGION" || echo "Component might already exist, continuing..."

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

# Install Greengrass
echo "Installing Greengrass Core..."
ssh -i ~/.ssh/greengrass-key -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" \
    "cd /tmp/GreengrassInstaller && sudo -E java -Droot=\"/greengrass/v2\" \
    -Dlog.store=FILE \
    -jar ./lib/Greengrass.jar \
    --aws-region $AWS_REGION \
    --thing-name $IOT_THING_NAME \
    --thing-group-name edge-llm-greengrass-group \
    --tes-role-alias-name $ROLE_ALIAS \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true \
    --deploy-dev-tools true"

# Start Greengrass service
echo "Starting Greengrass service..."
ssh -i ~/.ssh/greengrass-key -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" \
    "sudo systemctl start greengrass && sudo systemctl enable greengrass"

# Add ggc_user to docker group for InfluxDB component
echo "Adding ggc_user to docker group for InfluxDB component..."
ssh -i ~/.ssh/greengrass-key -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" \
    "sudo usermod -aG docker ggc_user"

# Restart Greengrass to apply group membership changes
echo "Restarting Greengrass to apply docker group membership..."
ssh -i ~/.ssh/greengrass-key -o StrictHostKeyChecking=no ec2-user@"$EC2_PUBLIC_IP" \
    "sudo systemctl restart greengrass"

echo "Waiting for Greengrass to be fully ready after restart..."
sleep 45

# Step 6: Wait for Greengrass Thing Group to be created
echo "Step 6: Waiting for IoT Thing Group to be created by Greengrass..."
while ! aws iot describe-thing-group --thing-group-name edge-llm-greengrass-group --region "$AWS_REGION" >/dev/null 2>&1; do
    echo "Waiting for Thing Group to be created..."
    sleep 10
done

# Verify Thing is in the group
echo "Verifying Thing is registered..."
while ! aws iot describe-thing --thing-name "$IOT_THING_NAME" --region "$AWS_REGION" >/dev/null 2>&1; do
    echo "Waiting for IoT Thing to be registered..."
    sleep 10
done

echo "IoT resources ready. Creating Greengrass deployment..."

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
    "aws.greengrass.DockerApplicationManager": {
      "componentVersion": "2.0.11"
    },
    "com.edge.llm.InfluxDB": {
      "componentVersion": "1.0.0"
    },
    "com.edge.llm.Grafana": {
      "componentVersion": "1.0.15"
    },
    "com.edge.llm.ChatBotUI": {
      "componentVersion": "$CHATBOT_VERSION",
      "configurationUpdate": {
        "merge": "{\"webPort\": 8080, \"chatHistoryLimit\": 50, \"enableDebugMode\": true}"
      }
    },
    "com.edge.llm.SensorSimulator": {
      "componentVersion": "$SENSOR_VERSION",
      "configurationUpdate": {
        "merge": "{\"sensorCount\": 5, \"anomalyRate\": 0.1, \"publishInterval\": 10}"
      }
    }
  },
  "deploymentPolicies": {
    "failureHandlingPolicy": "DO_NOTHING",
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

# Step 7: Wait for deployment to complete
echo "Step 7: Waiting for deployment to complete..."
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
echo "  🤖 ChatBot UI (CodeLlama-7B): http://$EC2_PUBLIC_IP:8080"
echo "  📊 Grafana Dashboard: http://$EC2_PUBLIC_IP:3000 (admin/admin) - Running as Greengrass Component"
echo "  💾 InfluxDB UI: http://$EC2_PUBLIC_IP:8086 (admin/admin123) - Running as Greengrass Component"
echo "  🔌 SSH Access: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP"
echo ""
echo "Note: InfluxDB and Grafana now run as Greengrass components in Docker containers for better lifecycle management."
echo ""
echo "System Status Commands:"
echo "  Check components: aws greengrassv2 list-core-devices --region $AWS_REGION"
echo "  View deployment: aws greengrassv2 get-deployment --deployment-id $DEPLOYMENT_ID --region $AWS_REGION"
echo ""
echo "Troubleshooting Commands:"
echo "  Component logs: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log'"
echo "  Greengrass status: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'sudo systemctl status greengrass'"
echo "  InfluxDB container: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'sudo docker ps --filter name=greengrass-influxdb'"
echo "  Grafana container: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'sudo docker ps --filter name=greengrass-grafana'"
echo "  All containers: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'sudo docker ps'"
echo "  GPU usage: ssh -i ~/.ssh/greengrass-key ec2-user@$EC2_PUBLIC_IP 'nvidia-smi'"
echo ""
echo "Try asking the ChatBot:"
echo "  • 'What is the current system status?'"
echo "  • 'Show me temperature readings'"
echo "  • 'Are there any anomalies detected?'"
echo "  • 'List all available sensors'"
echo ""