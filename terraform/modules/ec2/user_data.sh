#!/bin/bash
set -e

# Update system
yum update -y

# Install dependencies
yum install -y java-11-amazon-corretto python3 python3-pip docker

# Start Docker service
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

# Create directory for Greengrass
mkdir -p /greengrass/v2
chmod 755 /greengrass

# Download Greengrass Core software
cd /tmp
wget -q https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller
rm greengrass-nucleus-latest.zip

# Note: Actual Greengrass installation will be done via deployment script
# with proper credentials and configuration

echo "EC2 instance prepared for Greengrass Core installation"