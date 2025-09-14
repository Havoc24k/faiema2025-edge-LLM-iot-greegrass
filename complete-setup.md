# Complete Greengrass Setup Instructions

## Current Status
✅ Infrastructure deployed successfully
✅ EC2 instance running: `i-0fb0211f816900510` (63.180.46.1)
✅ Components registered in AWS IoT Greengrass
✅ Deployment created: `ed51ba89-ac06-4e30-a0c9-e08612ba8dd2`

⏳ **Missing**: Greengrass Core device registration

## Manual Steps to Complete Setup

### Option 1: Wait for User Data (Recommended)
The EC2 user data script is installing all dependencies. Wait 15-20 minutes, then:

```bash
# Check if user data completed
AWS_PROFILE=Rhodes aws ssm send-command \
  --instance-ids i-0fb0211f816900510 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["test -f /tmp/greengrass-ready && echo READY || echo PENDING"]' \
  --region eu-central-1
```

### Option 2: SSH Manual Installation
If you have SSH access:

```bash
# Connect to EC2
ssh ec2-user@63.180.46.1

# Check if user data completed
test -f /tmp/greengrass-ready && echo "User data complete" || echo "Still running"

# Install Greengrass manually
cd /tmp/GreengrassInstaller
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE -jar ./lib/Greengrass.jar \
  --aws-region eu-central-1 \
  --thing-name edge-llm-greengrass-core \
  --thing-group-name edge-llm-greengrass-group \
  --tes-role-alias-name edge-llm-greengrass-TokenExchangeRoleAlias \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true \
  --deploy-dev-tools true

# Start services
sudo systemctl start greengrass
sudo systemctl enable greengrass
```

### Verify Installation
Once Greengrass is installed, check:

```bash
# Check deployment status
AWS_PROFILE=Rhodes aws greengrassv2 get-deployment \
  --deployment-id ed51ba89-ac06-4e30-a0c9-e08612ba8dd2 \
  --region eu-central-1

# List Greengrass core devices
AWS_PROFILE=Rhodes aws greengrassv2 list-core-devices --region eu-central-1
```

### Access Services
Once complete, access:
- **ChatBot UI**: http://63.180.46.1:8080
- **Grafana**: http://63.180.46.1:3000 (admin/admin)
- **InfluxDB**: http://63.180.46.1:8086 (admin/admin123)

## Troubleshooting
If deployment fails, check logs on EC2:
```bash
sudo tail -f /greengrass/v2/logs/greengrass.log
sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log
```