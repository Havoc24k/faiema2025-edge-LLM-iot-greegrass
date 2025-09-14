#!/bin/bash
set -e

# Variables
PROJECT_NAME="${project_name}"
AWS_REGION="${aws_region}"

# Update system
yum update -y

# Install required packages
yum install -y \
    java-11-amazon-corretto \
    python3 \
    python3-pip \
    git \
    docker \
    wget \
    unzip \
    tar

# Install NVIDIA drivers for GPU support
yum install -y gcc kernel-devel-$(uname -r)

# Install NVIDIA CUDA drivers for Amazon Linux 2023
wget https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-keyring-1.1-1.noarch.rpm
rpm -i cuda-keyring-1.1-1.noarch.rpm
yum clean all
yum -y install cuda-toolkit-12-3
yum -y install nvidia-driver-545

# Add nvidia-container-runtime for Docker GPU support
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | \
    tee /etc/yum.repos.d/nvidia-docker.repo
yum clean expire-cache
yum install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
systemctl start docker
systemctl enable docker

# Configure Docker daemon for GPU support
cat > /etc/docker/daemon.json <<EOF
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
EOF

systemctl restart docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Create greengrass user and group
useradd -r -m -U -s /bin/false ggc_user
groupadd -r ggc_group

# Download and extract Greengrass
cd /tmp
wget https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller

# Create Greengrass root directory
mkdir -p /greengrass/v2

# Install Python packages for components
pip3 install --upgrade pip
pip3 install \
    flask \
    requests \
    torch --index-url https://download.pytorch.org/whl/cu121 \
    transformers \
    accelerate \
    awsiotsdk \
    influxdb-client

# Install InfluxDB 2.x
echo "Installing InfluxDB..."
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.5-1.x86_64.rpm
yum localinstall -y influxdb2-2.7.5-1.x86_64.rpm
systemctl start influxdb
systemctl enable influxdb

# Configure InfluxDB (initial setup)
influx setup \
    --username admin \
    --password admin123 \
    --org edge-llm \
    --bucket sensors \
    --retention 30d \
    --force

# Get InfluxDB token for Grafana
INFLUX_TOKEN=$(influx auth list --json | python3 -c "import sys, json; print(json.loads(sys.stdin.read())[0]['token'])")
echo "INFLUX_TOKEN=$INFLUX_TOKEN" > /etc/influxdb-token

# Install Grafana
echo "Installing Grafana..."
cat > /etc/yum.repos.d/grafana.repo <<'GRAFANA_REPO'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
GRAFANA_REPO

yum install -y grafana

# Configure Grafana
cat > /etc/grafana/provisioning/datasources/influxdb.yaml <<DATASOURCE
apiVersion: 1

datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://localhost:8086
    jsonData:
      version: Flux
      organization: edge-llm
      defaultBucket: sensors
      tlsSkipVerify: true
    secureJsonData:
      token: $INFLUX_TOKEN
DATASOURCE

# Start Grafana
systemctl start grafana-server
systemctl enable grafana-server

# Download TinyLlama model cache (pre-download for faster component startup)
python3 -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

print('Pre-downloading TinyLlama model...')
model_name = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map='auto'
)
print('Model downloaded successfully')
"

# Create marker file to indicate user data completion
touch /tmp/greengrass-ready

echo "User data script completed. Ready for Greengrass installation."