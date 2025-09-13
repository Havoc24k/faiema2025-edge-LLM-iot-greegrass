# Deployment Pipeline

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed (v1.0+)
3. SSH key pair for EC2 access
4. Docker installed on local machine for testing

## Deployment Steps

### 1. Deploy the Infrastructure and Components

```bash
chmod +x deploy.sh
./deploy.sh
```

This script will:
- Deploy AWS infrastructure using Terraform
- Upload Greengrass components to S3
- Install Greengrass Core on EC2
- Deploy components to the edge device
- Start Grafana for visualization

### 2. Access the Demo

After deployment:
- **Grafana Dashboard**: `http://<EC2_PUBLIC_IP>:3000`
  - Username: `admin`
  - Password: `admin`

### 3. Monitor the System

View component logs on EC2:
```bash
ssh ec2-user@<EC2_PUBLIC_IP>
sudo tail -f /greengrass/v2/logs/com.edge.llm.*.log
```

Check deployment status:
```bash
aws greengrassv2 list-deployments --region us-east-1
```

### 4. Clean Up

To destroy all resources:
```bash
chmod +x destroy.sh
./destroy.sh
```

## Component Management

### Update Component Version

1. Modify component code
2. Update version in `recipe.json`
3. Re-run deployment script

### Configuration Updates

Edit component configurations in `deployment.json` and redeploy:
```bash
aws greengrassv2 create-deployment --cli-input-json file://deployment.json
```

## Troubleshooting

### Common Issues

1. **Greengrass installation fails**
   - Check EC2 instance has proper IAM roles
   - Verify IoT certificates are created

2. **Components not starting**
   - Check logs: `/greengrass/v2/logs/`
   - Verify S3 artifacts are uploaded

3. **Grafana not accessible**
   - Check security group allows port 3000
   - Verify Docker is running on EC2

4. **LLM inference slow**
   - Consider using larger EC2 instance
   - Optimize model quantization settings