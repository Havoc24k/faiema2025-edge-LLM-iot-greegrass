# Edge LLM IoT Greengrass Deployment Guide

This guide will help you deploy the complete Edge LLM system from scratch using just this repository and an AWS account.

## 🏗️ Architecture Overview

The system consists of:
- **AWS Infrastructure**: EC2 instance with GPU support for LLM inference
- **AWS IoT Greengrass**: Edge runtime for component management
- **Edge LLM Components**: ChatBot UI with CodeLlama-7B model
- **Sensor Simulation**: Mock sensor data generation
- **Data Stack**: InfluxDB for time-series data storage
- **Monitoring**: Grafana dashboards for visualization

## 📋 Prerequisites

### Required Tools
- **AWS CLI v2** with configured credentials
- **Terraform** v1.0+ for infrastructure provisioning
- **SSH client** for instance access
- **Git** for repository management

### AWS Account Requirements
- AWS account with appropriate permissions for:
  - EC2, VPC, IAM, S3, IoT Core, Greengrass
  - Ability to create GPU instances (g4dn.xlarge)
- AWS SSO or IAM user with programmatic access

### AWS Permissions Needed
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*", "vpc:*", "iam:*", "s3:*",
        "iot:*", "greengrass:*", "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🚀 Deployment Steps

### Step 1: Clone and Setup Repository

```bash
git clone <repository-url>
cd faiema2025-edge-LLM-iot-greegrass
```

### Step 2: Configure AWS Credentials

```bash
# Option A: AWS SSO
aws configure sso
aws sso login

# Option B: IAM credentials
aws configure
```

Test credentials:
```bash
aws sts get-caller-identity
```

### Step 3: Deploy the System

The deployment script will automatically generate SSH keys if they don't exist.

```bash
# Deploy with default settings
./deploy-aws.sh

# Or customize the deployment
export IOT_THING_NAME="MyEdgeLLMDevice-$(date +%s)"
export AWS_REGION="us-west-2"
export AWS_PROFILE="my-profile"
./deploy-aws.sh
```

**Configuration Options:**
- `IOT_THING_NAME`: Name for your Greengrass device (default: EdgeLLMDemoAWS-timestamp)
- `AWS_REGION`: AWS region for deployment (default: eu-central-1)
- `AWS_PROFILE`: AWS profile to use (default: Rhodes)

**Note**: If you don't have SSH keys at `~/.ssh/greengrass-key`, the script will automatically generate them for you.

**The deploy script will:**
1. Auto-generate SSH keys if needed
2. Deploy infrastructure with Terraform
3. Wait for EC2 to be ready and accessible
4. Upload component artifacts to S3
5. Register components in Greengrass
6. Install InfluxDB, Grafana, and Greengrass Core via SSH
7. Wait for IoT resources and create deployment

### Step 4: Wait for Deployment

The script will automatically:
1. Wait for IoT Thing Group to be created by Greengrass
2. Verify IoT Thing registration
3. Create deployment targeting the Thing Group
4. Wait for deployment completion

You can monitor progress manually:
```bash
# Check Greengrass device status
aws greengrassv2 list-core-devices --region eu-central-1

# Monitor deployment status
aws greengrassv2 list-deployments \
  --target-arn "arn:aws:iot:eu-central-1:$(aws sts get-caller-identity --query Account --output text):thinggroup/edge-llm-greengrass-group" \
  --region eu-central-1
```

Wait until device status shows **HEALTHY**.

### Step 5: Access Services

Once deployment is complete, access your services:

#### ChatBot Web UI
```
http://<EC2_PUBLIC_IP>:8080
```
- Interactive chat interface with CodeLlama-7B
- Ask questions about sensor data and system status

#### Grafana Dashboard
```
http://<EC2_PUBLIC_IP>:3000
```
- **Username**: admin
- **Password**: admin (change on first login)
- Import dashboard from `grafana-dashboards/edge-llm-dashboard.json`

#### InfluxDB UI
```
http://<EC2_PUBLIC_IP>:8086
```
- **Username**: admin
- **Password**: admin123
- Browse sensor data and metrics

### Step 6: Verify System Operation

```bash
# SSH into the instance
ssh -i ~/.ssh/greengrass-key ec2-user@<EC2_PUBLIC_IP>

# Check Greengrass logs
sudo tail -f /greengrass/v2/logs/greengrass.log

# Check component logs
sudo tail -f /greengrass/v2/logs/com.edge.llm.ChatBotUI.log
sudo tail -f /greengrass/v2/logs/com.edge.llm.SensorSimulator.log

# Check system resources
nvidia-smi  # GPU utilization
htop        # System performance
```

## 🧪 Testing the System

### Test ChatBot Functionality
1. Navigate to ChatBot UI: `http://<EC2_PUBLIC_IP>:8080`
2. Try these example queries:
   - "What is the current system status?"
   - "Show me temperature readings"
   - "Are there any anomalies detected?"
   - "List all available sensors"

### Test Sensor Data Flow
1. Check InfluxDB for incoming data:
   ```bash
   curl "http://<EC2_PUBLIC_IP>:8086/query?db=sensors&q=SELECT * FROM sensor_data LIMIT 10"
   ```

2. Verify Grafana visualization:
   - Open Grafana dashboard
   - Confirm real-time sensor data charts

### Test AI/LLM Integration
- Ask the ChatBot complex questions about sensor patterns
- Verify it can analyze JSON sensor data and provide insights
- Test anomaly detection discussions

## 🔧 Configuration

### Adjust Component Settings

Edit component configurations via AWS Console or CLI:

```bash
# Update ChatBot configuration
aws greengrassv2 create-deployment \
  --deployment-name "EdgeLLM-Config-Update" \
  --target-arn "arn:aws:iot:eu-central-1:$(aws sts get-caller-identity --query Account --output text):thinggroup/edge-llm-greengrass-group" \
  --components '{
    "com.edge.llm.ChatBotUI": {
      "componentVersion": "1.0.5",
      "configurationUpdate": {
        "merge": "{\"webPort\": 8080, \"chatHistoryLimit\": 100, \"enableDebugMode\": false}"
      }
    }
  }' \
  --region eu-central-1
```

### Scale Sensor Simulation

```bash
# Increase sensor count and frequency
aws greengrassv2 create-deployment \
  --deployment-name "EdgeLLM-Scale-Sensors" \
  --target-arn "arn:aws:iot:eu-central-1:$(aws sts get-caller-identity --query Account --output text):thinggroup/edge-llm-greengrass-group" \
  --components '{
    "com.edge.llm.SensorSimulator": {
      "componentVersion": "1.0.1",
      "configurationUpdate": {
        "merge": "{\"sensorCount\": 10, \"anomalyRate\": 0.15, \"publishInterval\": 5}"
      }
    }
  }' \
  --region eu-central-1
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Greengrass Device Not Healthy
```bash
# Check Greengrass logs
ssh -i ~/.ssh/greengrass-key ec2-user@<EC2_PUBLIC_IP>
sudo tail -f /greengrass/v2/logs/greengrass.log

# Restart Greengrass service
sudo systemctl restart greengrass
```

#### 2. Components Not Starting
```bash
# Check component logs
sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log

# Verify artifacts in S3
aws s3 ls s3://$(terraform output -raw s3_bucket)/com.edge.llm.ChatBotUI/ --recursive
```

#### 3. GPU Not Available
```bash
# Check NVIDIA driver installation
nvidia-smi

# If missing, reinstall drivers
sudo yum install -y nvidia-driver-latest-dkms cuda-drivers
sudo reboot
```

#### 4. ChatBot Not Responding
```bash
# Check Python dependencies
pip3 list | grep -E "(torch|transformers|flask)"

# Check model download status
ls -la /home/ec2-user/.cache/huggingface/
```

#### 5. InfluxDB Connection Issues
```bash
# Check InfluxDB service
sudo systemctl status influxdb
sudo journalctl -u influxdb -f

# Test database connectivity
curl http://localhost:8086/ping
```

### Performance Optimization

#### GPU Memory Optimization
```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Adjust model precision in ChatBot component if needed
# (Edit component configuration to use smaller models or quantization)
```

#### Instance Size Recommendations
- **Development**: g4dn.xlarge (4 vCPU, 16GB RAM, 1x Tesla T4)
- **Production**: g4dn.2xlarge (8 vCPU, 32GB RAM, 1x Tesla T4)
- **High Load**: g5.xlarge (4 vCPU, 16GB RAM, 1x A10G)

## 🧹 Cleanup

### Remove All Resources

```bash
cd infrastructure

# Destroy infrastructure
terraform destroy

# Verify cleanup
aws ec2 describe-instances --region eu-central-1 \
  --filters "Name=tag:Project,Values=edge-llm-greengrass"
```

### Partial Cleanup (Keep Infrastructure)

```bash
# Remove only Greengrass deployment
aws greengrassv2 create-deployment \
  --deployment-name "EdgeLLM-Cleanup" \
  --target-arn "arn:aws:iot:eu-central-1:$(aws sts get-caller-identity --query Account --output text):thinggroup/edge-llm-greengrass-group" \
  --components '{}' \
  --region eu-central-1

# Stop EC2 instance to save costs
aws ec2 stop-instances --instance-ids $(terraform output -raw ec2_instance_id) --region eu-central-1
```

## 📊 Expected Costs

### AWS Resources (us-east-1 pricing)
- **g4dn.xlarge**: ~$0.526/hour
- **EBS gp3 100GB**: ~$8/month
- **Elastic IP**: ~$3.65/month (when not attached)
- **S3 storage**: ~$0.023/GB/month
- **Data transfer**: ~$0.09/GB outbound

### Monthly Estimate
- **24/7 operation**: ~$380/month
- **8 hours/day**: ~$127/month
- **Development use**: ~$50/month

## 🔗 Useful Commands

```bash
# Check deployment status
aws greengrassv2 get-deployment --deployment-id <deployment-id> --region eu-central-1

# List all components
aws greengrassv2 list-components --scope PRIVATE --region eu-central-1

# View component logs remotely
aws logs tail /aws/greengrass/UserComponent/com.edge.llm.ChatBotUI --region eu-central-1

# Update component version
aws greengrassv2 create-component-version --cli-input-json file://components/chatbot-ui/recipe.json

# SSH tunnel for secure access
ssh -i ~/.ssh/greengrass-key -L 8080:localhost:8080 -L 3000:localhost:3000 ec2-user@<EC2_PUBLIC_IP>
```

## 📚 Additional Resources

- [AWS IoT Greengrass Documentation](https://docs.aws.amazon.com/greengrass/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [CodeLlama Model Documentation](https://huggingface.co/codellama/CodeLlama-7b-Instruct-hf)
- [InfluxDB Documentation](https://docs.influxdata.com/influxdb/)
- [Grafana Documentation](https://grafana.com/docs/)

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review AWS CloudWatch logs
3. Verify all prerequisites are met
4. Ensure AWS quotas allow GPU instances in your region

---

**⚠️ Important Notes:**
- GPU instances have limited availability in some regions
- Ensure you have sufficient EC2 quotas for g4dn instances
- Monitor costs closely during development
- Always stop/terminate resources when not in use to avoid charges