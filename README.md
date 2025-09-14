# Edge-Native LLM Inference with AWS IoT Greengrass

**GPU-Accelerated AI Reasoning for Industrial IoT Using Frugal Architecture Principles**

## 🎯 Demo Overview

This project demonstrates GPU-accelerated edge-native LLM inference for industrial IoT using AWS IoT Greengrass, following frugal architecture principles to maximize value while minimizing complexity and cost.

## ✨ Key Features

1. **GPU-Accelerated Edge LLM**: TinyLlama-1.1B with NVIDIA Tesla T4 GPU support (2-3 second responses)
2. **Interactive ChatBot Web UI**: Natural language interface for querying real-time sensor data
3. **Industrial Sensor Simulation**: Realistic sensor data with configurable anomaly injection
4. **Real-Time Visualization**: InfluxDB + Grafana dashboards for comprehensive monitoring
5. **Cost-Optimized Architecture**: 90% cost reduction vs cloud-based inference
6. **Auto-Restart Services**: All components configured for reliability after reboot
7. **One-Click Deployment**: Complete Terraform infrastructure with GPU drivers

## 🏗️ Architecture Benefits

- **Ultra-Low Latency**: GPU-accelerated responses in 2-3 seconds
- **Improved Reliability**: Operates offline without internet connectivity
- **Enhanced Security**: Sensitive data never leaves the facility
- **Cost Efficiency**: No cloud API calls or data transfer costs
- **Production Ready**: Auto-restart services and comprehensive monitoring

## 🚀 Quick Start

### 🖥️ **Local Development (2 minutes)**
```bash
./run-local.sh
```
Access: http://localhost:3000 (Grafana) | http://localhost:8080 (ChatBot)

### 🏭 **AWS Production Deployment (15 minutes)**
```bash
cd infrastructure
terraform init
terraform apply -auto-approve

# SSH access (optional)
ssh -i ~/.ssh/greengrass-key ec2-user@<EC2_IP>
```

**Access After Deployment:**
- **ChatBot UI**: `http://<EC2_IP>:8080`
- **Grafana**: `http://<EC2_IP>:3000` (admin/admin)
- **InfluxDB**: `http://<EC2_IP>:8086` (admin/admin123)

## 📊 System Performance

### GPU Acceleration (Tesla T4)
- **Model**: TinyLlama-1.1B-Chat-v1.0
- **Response Time**: 2-3 seconds with GPU vs 15-20 seconds CPU-only
- **VRAM Usage**: ~2.3GB for optimal performance
- **Precision**: FP16 for memory efficiency

### ChatBot Capabilities

#### **Real-Time Sensor Queries**
```
User: "Show me temperature readings"
Bot: "🌡️ Current temperature: 45.2°C in zone_1. Based on 12 recent readings from InfluxDB."

User: "Are there any pressure anomalies?"
Bot: "⚠️ Detected 2 pressure anomalies: eq_102 exceeded 195kPa threshold at 14:23."
```

#### **System Status Monitoring**
```
User: "List all available sensors"
Bot: "I'm monitoring 15 sensors: 5 temperature, 5 pressure, 5 vibration sensors across 3 zones."

User: "What's the GPU utilization?"
Bot: "Tesla T4 GPU is running at 45% utilization, temperature 52°C, using 2.3GB VRAM."
```

## 🏗️ Components

### Custom Components (Minimal, Value-Added)
- **com.edge.llm.SensorSimulator**: Industrial sensor data generation
- **com.edge.llm.ChatBotUI**: GPU-accelerated LLM with web interface

### Infrastructure Services
- **InfluxDB**: Time-series database for sensor data
- **Grafana**: Real-time visualization and alerting
- **Docker**: Containerized services with auto-restart

## 💰 Cost Analysis (100 Devices)

- **Traditional Cloud**: $52,500/year
- **Edge LLM**: $5,000/year
- **Savings**: 90% cost reduction

## 🛠️ Development Workflow

### 1. Local Development
```bash
# Quick local testing with full Greengrass runtime
./run-local.sh

# Access local services
open http://localhost:8080  # ChatBot
open http://localhost:3000  # Grafana
```

### 2. AWS Deployment
```bash
# Deploy to AWS with GPU support
cd infrastructure
terraform apply

# Monitor deployment
AWS_PROFILE=Rhodes aws greengrassv2 list-core-devices --region eu-central-1
```

### 3. Component Updates
```bash
# Update component version
AWS_PROFILE=Rhodes aws s3 cp components/chatbot-ui/ s3://bucket/path/ --recursive
AWS_PROFILE=Rhodes aws greengrassv2 create-component-version --inline-recipe file://recipe.json
```

## 🔧 Configuration

### GPU Configuration (Automatic)
- **NVIDIA Driver**: 545 (installed via user_data.sh)
- **CUDA Toolkit**: 12.3
- **Docker GPU Support**: nvidia-container-toolkit
- **PyTorch**: CUDA 12.1 optimized

### Service Configuration
```bash
# All services configured for auto-restart
systemctl status greengrass    # AWS IoT Greengrass
systemctl status docker        # Docker Engine
systemctl status influxdb     # InfluxDB Database
systemctl status grafana-server  # Grafana Dashboard
```

## 📁 Project Structure

```
├── infrastructure/           # Terraform AWS deployment
│   ├── main.tf              # Complete infrastructure as code
│   └── user_data.sh         # EC2 initialization with GPU drivers
├── components/              # Greengrass components
│   ├── chatbot-ui/          # GPU-accelerated LLM web interface
│   └── sensor-simulator/    # Industrial sensor data generation
├── grafana-dashboards/      # Pre-configured visualization
├── deploy-aws.sh           # One-click AWS deployment
└── run-local.sh            # Local development environment
```

## 🚨 Troubleshooting

### Common Issues

**GPU Not Detected**
```bash
# Check NVIDIA driver status
nvidia-smi
# Should show Tesla T4 with ~2.3GB usage
```

**Components Not Starting**
```bash
# Check Greengrass logs
sudo tail -f /greengrass/v2/logs/greengrass.log
sudo tail -f /greengrass/v2/logs/com.edge.llm.ChatBotUI.log
```

**Services Not Auto-Restarting**
```bash
# Verify service status
systemctl status greengrass docker influxdb grafana-server
# All should show "active (running)" and "enabled"
```

## 🎯 Production Deployment Targets

- **Demo Environment**: EC2 g4dn.xlarge (Tesla T4 GPU)
- **Edge Production**: NVIDIA Jetson, industrial edge computers
- **Scale Deployment**: Fleet management via AWS IoT Device Management

## 📈 Monitoring & Alerts

### Grafana Dashboards
- Real-time sensor readings with 5-second refresh
- GPU utilization and temperature monitoring
- Component health and deployment status
- Custom anomaly detection thresholds

### InfluxDB Metrics
- Sensor data with proper time-series indexing
- System performance metrics (CPU, memory, GPU)
- Component lifecycle events and errors

---

**Built with Frugal Architecture Principles**: Simple, measurable, and aligned with business needs. Every component serves a purpose, every decision maximizes value.