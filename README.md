# Edge-Native LLM Inference with AWS IoT Greengrass

**Enabling AI Reasoning in Industrial Environments Using Frugal Architecture Principles**

## Demo Overview

This project demonstrates edge-native LLM inference for industrial IoT using AWS IoT Greengrass, following frugal architecture principles to maximize value while minimizing complexity and cost.

## Key Features

1. **Edge-Native LLM Inference**: Deploy TinyLlama 1.1B model with 4-bit quantization for real-time analysis
2. **Interactive ChatBot Web UI**: Natural language interface for querying sensor data and system status
3. **Industrial Sensor Simulation**: Generate realistic sensor data with configurable anomaly injection
4. **Real-Time Visualization**: Local Grafana dashboards using official AWS Greengrass Labs components
5. **Cost-Optimized Architecture**: 90% cost reduction vs cloud-based inference
6. **Automated Deployment**: Terraform infrastructure with one-click deployment pipeline
7. **Frugal Design**: Leverages official components, eliminates redundancy, follows KISS/DRY principles

## Architecture Benefits

- **Reduced Latency**: Local inference in milliseconds vs seconds for cloud
- **Improved Reliability**: Operates offline without internet connectivity
- **Enhanced Security**: Sensitive data never leaves the facility
- **Cost Efficiency**: No cloud API calls or data transfer costs
- **Simplified Maintenance**: Uses official AWS Greengrass Labs components

## Components

### Custom Components (Minimal, Value-Added)
- **Sensor Simulator**: Generates industrial sensor data
- **LLM Inference Engine**: Edge-optimized TinyLlama with real-time analysis
- **ChatBot Web UI**: Interactive natural language interface for sensor queries
- **Telemetry Bridge**: Lightweight data transformation layer

### Official AWS Components (Battle-Tested)
- **aws.greengrass.labs.dashboard.InfluxDBGrafana**: Complete visualization stack
- **aws.greengrass.labs.telemetry.InfluxDBPublisher**: Time-series data management

## Quick Start

### 🚀 **Local Development (30 seconds)**
```bash
docker-compose up -d
```
Access: http://localhost:3000 (Grafana) | http://localhost:8080 (ChatBot)

### 🏭 **Production AWS Deployment**
```bash
cd pipeline && chmod +x deploy-v2.sh && ./deploy-v2.sh
```
Access: `http://<EC2_IP>:3000` (Grafana) | `http://<EC2_IP>:8080` (ChatBot)

### 📋 **All Deployment Options**
See [DEPLOYMENT_OPTIONS.md](./DEPLOYMENT_OPTIONS.md) for complete comparison

## Deployment Targets

- **Demo**: EC2 t3.medium instance
- **Production**: Raspberry Pi, NVIDIA Jetson, or industrial edge computers
- **Scale**: Fleet deployment via AWS IoT Device Management

## Cost Analysis

- **Traditional Cloud**: $52,500/year for 100 devices
- **Edge LLM**: $5,000/year for 100 devices
- **Savings**: 90% cost reduction
