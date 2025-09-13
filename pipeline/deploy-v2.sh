#!/bin/bash
set -e

# Configuration
PROJECT_NAME="${PROJECT_NAME:-edge-llm-greengrass}"
ENVIRONMENT="${ENVIRONMENT:-demo}"
AWS_REGION="${AWS_REGION:-us-east-1}"
COMPONENT_VERSION="${COMPONENT_VERSION:-1.0.0}"

# Official AWS Greengrass Labs component versions
INFLUXDB_GRAFANA_VERSION="2.0.7"
INFLUXDB_PUBLISHER_VERSION="1.0.0"

echo "========================================="
echo "Edge LLM IoT Greengrass Deployment v2"
echo "========================================="
echo "Project: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Using official AWS Greengrass Labs components"
echo ""

# Step 1: Deploy Infrastructure
echo "Step 1: Deploying infrastructure with Terraform..."
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Get outputs
BUCKET_NAME=$(terraform output -raw artifacts_bucket)
EC2_IP=$(terraform output -raw ec2_public_ip)
EC2_ID=$(terraform output -raw ec2_instance_id)
THING_NAME=$(terraform output -raw iot_thing_name)

cd ..

echo "Infrastructure deployed:"
echo "  - S3 Bucket: $BUCKET_NAME"
echo "  - EC2 Instance: $EC2_ID ($EC2_IP)"
echo "  - IoT Thing: $THING_NAME"
echo ""

# Step 2: Build and upload custom components only
echo "Step 2: Building and uploading custom Greengrass components..."

upload_component() {
    local component_name=$1
    local component_path=$2
    
    echo "  Building $component_name..."
    
    # Update S3 URIs in recipe
    sed -i "s|BUCKET_NAME|${BUCKET_NAME}|g" "${component_path}/recipe.json"
    sed -i "s|COMPONENT_NAME|${component_name}|g" "${component_path}/recipe.json"
    sed -i "s|COMPONENT_VERSION|${COMPONENT_VERSION}|g" "${component_path}/recipe.json"
    
    # Upload artifacts to S3
    for file in "${component_path}"/*.py "${component_path}"/*.txt "${component_path}"/*.json "${component_path}"/*.js "${component_path}"/*.css "${component_path}"/*.html; do
        if [ -f "${file}" ] && [ "$(basename "${file}")" != "recipe.json" ]; then
            aws s3 cp "${file}" "s3://${BUCKET_NAME}/${component_name}/${COMPONENT_VERSION}/" --region "${AWS_REGION}"
        fi
    done
    
    # Upload subdirectories for ChatBot UI
    if [ -d "${component_path}/static" ]; then
        aws s3 cp "${component_path}/static/" "s3://${BUCKET_NAME}/${component_name}/${COMPONENT_VERSION}/static/" --recursive --region "${AWS_REGION}"
    fi
    
    if [ -d "${component_path}/templates" ]; then
        aws s3 cp "${component_path}/templates/" "s3://${BUCKET_NAME}/${component_name}/${COMPONENT_VERSION}/templates/" --recursive --region "${AWS_REGION}"
    fi
    
    echo "  $component_name uploaded successfully"
}

# Upload only custom components
upload_component "com.edge.llm.SensorSimulator" "components/sensor-simulator"
upload_component "com.edge.llm.InferenceEngine" "components/llm-inference"
upload_component "com.edge.llm.TelemetryBridge" "components/telemetry-bridge"
upload_component "com.edge.llm.ChatBotUI" "components/chatbot-ui"

echo ""

# Step 3: Install Greengrass on EC2
echo "Step 3: Installing Greengrass Core on EC2 instance..."

cat > /tmp/install-greengrass.sh << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

# Wait for user data to complete
while [ ! -f /tmp/GreengrassInstaller/bin/greengrass.service.template ]; do
    echo "Waiting for Greengrass download to complete..."
    sleep 5
done

# Install Greengrass Core with Docker support
cd /tmp/GreengrassInstaller
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./lib/Greengrass.jar \
  --aws-region $AWS_REGION \
  --thing-name $THING_NAME \
  --thing-group-name $PROJECT_NAME-$ENVIRONMENT-group \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true \
  --deploy-dev-tools true

# Add ggc_user to docker group for container management
sudo usermod -a -G docker ggc_user

echo "Greengrass Core installed successfully"
INSTALL_SCRIPT

# Copy and run installation script on EC2
aws ec2-instance-connect send-ssh-public-key \
    --instance-id "${EC2_ID}" \
    --instance-os-user ec2-user \
    --ssh-public-key file://~/.ssh/id_rsa.pub \
    --region "${AWS_REGION}" || true

scp -o StrictHostKeyChecking=no /tmp/install-greengrass.sh "ec2-user@${EC2_IP}:/tmp/"
ssh -o StrictHostKeyChecking=no "ec2-user@${EC2_IP}" "chmod +x /tmp/install-greengrass.sh && sudo AWS_REGION=${AWS_REGION} THING_NAME=${THING_NAME} PROJECT_NAME=${PROJECT_NAME} ENVIRONMENT=${ENVIRONMENT} /tmp/install-greengrass.sh"

echo ""

# Step 4: Create Greengrass deployment with official and custom components
echo "Step 4: Creating Greengrass deployment configuration..."

cat > deployment.json << DEPLOYMENT
{
  "targetArn": "arn:aws:iot:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):thinggroup/$PROJECT_NAME-$ENVIRONMENT-group",
  "deploymentName": "$PROJECT_NAME-edge-llm-deployment-v2",
  "components": {
    "aws.greengrass.Cli": {
      "componentVersion": "2.12.0"
    },
    "aws.greengrass.DockerApplicationManager": {
      "componentVersion": "2.0.10"
    },
    "aws.greengrass.labs.dashboard.InfluxDBGrafana": {
      "componentVersion": "$INFLUXDB_GRAFANA_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"InfluxDBPort\": 8086,
          \"InfluxDBDataPath\": \"/greengrass/v2/work/influxdb\",
          \"GrafanaPort\": 3000,
          \"GrafanaDataPath\": \"/greengrass/v2/work/grafana\",
          \"BridgeNetworkName\": \"greengrass-telemetry-bridge\"
        }"
      }
    },
    "aws.greengrass.labs.telemetry.InfluxDBPublisher": {
      "componentVersion": "$INFLUXDB_PUBLISHER_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"PublishInterval\": 5,
          \"OutputMetrics\": true
        }"
      }
    },
    "com.edge.llm.SensorSimulator": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"sensorCount\": 5,
          \"samplingIntervalMs\": 5000,
          \"anomalyProbability\": 0.05
        }"
      }
    },
    "com.edge.llm.InferenceEngine": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"modelName\": \"TinyLlama-1.1B-Chat\",
          \"batchSize\": 10,
          \"inferenceIntervalMs\": 30000
        }"
      }
    },
    "com.edge.llm.TelemetryBridge": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"sensorTopics\": [\"local/sensors/+\"],
          \"analysisTopics\": [\"local/analysis/results\"],
          \"dashboardPort\": 3000
        }"
      }
    },
    "com.edge.llm.ChatBotUI": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{
          \"webPort\": 8080,
          \"chatHistoryLimit\": 50,
          \"enableDebugMode\": true
        }"
      }
    }
  },
  "deploymentPolicies": {
    "failureHandlingPolicy": "ROLLBACK",
    "componentUpdatePolicy": {
      "timeoutInSeconds": 120,
      "action": "NOTIFY_COMPONENTS"
    }
  }
}
DEPLOYMENT

# Create the deployment
aws greengrassv2 create-deployment --cli-input-json file://deployment.json --region "${AWS_REGION}"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Access points:"
echo "  - Grafana Dashboard: http://$EC2_IP:3000"
echo "    Default credentials: admin / admin"
echo "    (The official component sets up authentication)"
echo ""
echo "  - ChatBot Web UI: http://$EC2_IP:8080"
echo "    Interactive chat interface for querying sensor data"
echo ""
echo "  - InfluxDB UI: http://$EC2_IP:8086"
echo "    Default credentials: admin / admin"
echo ""
echo "  - SSH to EC2: ssh ec2-user@$EC2_IP"
echo ""
echo "Monitor deployment status:"
echo "  aws greengrassv2 list-deployments --region $AWS_REGION"
echo ""
echo "View component logs on EC2:"
echo "  sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log"
echo "  sudo tail -f /greengrass/v2/logs/aws.greengrass.labs.*.log"
echo ""
echo "Using official AWS Greengrass Labs components:"
echo "  - aws.greengrass.labs.dashboard.InfluxDBGrafana v$INFLUXDB_GRAFANA_VERSION"
echo "  - aws.greengrass.labs.telemetry.InfluxDBPublisher v$INFLUXDB_PUBLISHER_VERSION"
echo ""