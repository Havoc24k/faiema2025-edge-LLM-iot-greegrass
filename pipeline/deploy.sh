#!/bin/bash
set -e

# Configuration
PROJECT_NAME="${PROJECT_NAME:-edge-llm-greengrass}"
ENVIRONMENT="${ENVIRONMENT:-demo}"
AWS_REGION="${AWS_REGION:-us-east-1}"
COMPONENT_VERSION="${COMPONENT_VERSION:-1.0.0}"

echo "========================================="
echo "Edge LLM IoT Greengrass Deployment"
echo "========================================="
echo "Project: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
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

# Step 2: Build and upload components
echo "Step 2: Building and uploading Greengrass components..."

# Function to build and upload component
upload_component() {
    local component_name=$1
    local component_path=$2
    
    echo "  Building $component_name..."
    
    # Update S3 URIs in recipe
    sed -i "s|BUCKET_NAME|$BUCKET_NAME|g" $component_path/recipe.json
    sed -i "s|COMPONENT_NAME|$component_name|g" $component_path/recipe.json
    sed -i "s|COMPONENT_VERSION|$COMPONENT_VERSION|g" $component_path/recipe.json
    
    # Upload artifacts to S3
    for file in $component_path/*.py $component_path/*.txt $component_path/*.sh; do
        if [ -f "$file" ]; then
            aws s3 cp "$file" "s3://$BUCKET_NAME/$component_name/$COMPONENT_VERSION/" --region $AWS_REGION
        fi
    done
    
    # Build Grafana config if needed
    if [ "$component_name" == "com.edge.llm.Grafana" ]; then
        cd $component_path
        bash create-config.sh
        aws s3 cp grafana-config.tar.gz "s3://$BUCKET_NAME/$component_name/$COMPONENT_VERSION/" --region $AWS_REGION
        cd -
    fi
    
    echo "  $component_name uploaded successfully"
}

# Upload all components
upload_component "com.edge.llm.SensorSimulator" "components/sensor-simulator"
upload_component "com.edge.llm.InferenceEngine" "components/llm-inference"
upload_component "com.edge.llm.Grafana" "components/grafana"

echo ""

# Step 3: Install Greengrass on EC2
echo "Step 3: Installing Greengrass Core on EC2 instance..."

# Create installation script
cat > /tmp/install-greengrass.sh << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

# Wait for user data to complete
while [ ! -f /tmp/GreengrassInstaller/bin/greengrass.service.template ]; do
    echo "Waiting for Greengrass download to complete..."
    sleep 5
done

# Install Greengrass Core
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

echo "Greengrass Core installed successfully"
INSTALL_SCRIPT

# Copy and run installation script on EC2
aws ec2-instance-connect send-ssh-public-key \
    --instance-id $EC2_ID \
    --instance-os-user ec2-user \
    --ssh-public-key file://~/.ssh/id_rsa.pub \
    --region $AWS_REGION || true

scp -o StrictHostKeyChecking=no /tmp/install-greengrass.sh ec2-user@$EC2_IP:/tmp/
ssh -o StrictHostKeyChecking=no ec2-user@$EC2_IP "chmod +x /tmp/install-greengrass.sh && sudo AWS_REGION=$AWS_REGION THING_NAME=$THING_NAME PROJECT_NAME=$PROJECT_NAME ENVIRONMENT=$ENVIRONMENT /tmp/install-greengrass.sh"

echo ""

# Step 4: Create Greengrass deployment
echo "Step 4: Creating Greengrass deployment configuration..."

cat > deployment.json << DEPLOYMENT
{
  "targetArn": "arn:aws:iot:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):thinggroup/$PROJECT_NAME-$ENVIRONMENT-group",
  "deploymentName": "$PROJECT_NAME-edge-llm-deployment",
  "components": {
    "com.edge.llm.SensorSimulator": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{\"sensorCount\":5,\"samplingIntervalMs\":5000}"
      }
    },
    "com.edge.llm.InferenceEngine": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{\"modelName\":\"TinyLlama-1.1B-Chat\",\"batchSize\":10}"
      }
    },
    "com.edge.llm.Grafana": {
      "componentVersion": "$COMPONENT_VERSION",
      "configurationUpdate": {
        "merge": "{\"grafanaPort\":3000,\"adminPassword\":\"admin\"}"
      }
    }
  }
}
DEPLOYMENT

# Create the deployment
aws greengrassv2 create-deployment --cli-input-json file://deployment.json --region $AWS_REGION

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Access points:"
echo "  - Grafana Dashboard: http://$EC2_IP:3000"
echo "    Username: admin"
echo "    Password: admin"
echo ""
echo "  - SSH to EC2: ssh ec2-user@$EC2_IP"
echo ""
echo "Monitor deployment status:"
echo "  aws greengrassv2 list-deployments --region $AWS_REGION"
echo ""
echo "View component logs on EC2:"
echo "  sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log"
echo ""