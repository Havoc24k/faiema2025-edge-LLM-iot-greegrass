# System Architecture

## Overview

This demo showcases edge-native LLM inference for industrial IoT using AWS IoT Greengrass. The system performs real-time analysis of sensor data using a locally deployed language model, providing immediate insights without cloud dependency.

## Components

### 1. Sensor Simulator
- Generates realistic industrial sensor data (temperature, pressure, vibration)
- Configurable anomaly injection for demo scenarios
- Publishes to local and cloud MQTT topics

### 2. LLM Inference Engine
- TinyLlama 1.1B model with 4-bit quantization
- Real-time anomaly detection and batch analysis
- Local inference without cloud API calls
- Memory-efficient deployment suitable for edge devices

### 3. Grafana Visualization
- Real-time dashboards for sensor data
- LLM analysis results display
- InfluxDB for time-series storage
- Dockerized deployment on edge device

## Data Flow

```
Sensors → MQTT Topics → LLM Inference → Analysis Results → Grafana
                ↓                              ↓
            InfluxDB                      IoT Core (Cloud)
```

## Cost Optimization (Frugal Architecture)

### Design Phase
- **Tiered Components**: Critical (LLM), Important (Grafana), Nice-to-have (Simulator)
- **Trade-offs**: Smaller model (1.1B) vs accuracy for edge deployment
- **Business Alignment**: Local inference reduces cloud API costs

### Measure Phase
- Component resource monitoring via Greengrass metrics
- Cost tracking through AWS Cost Explorer tags
- Performance metrics in Grafana dashboards

### Optimize Phase
- 4-bit quantization reduces memory by 75%
- Batch processing minimizes inference calls
- Local caching prevents redundant downloads

## Security Considerations

- All S3 buckets encrypted with AES256
- IAM roles follow least privilege principle
- Greengrass token exchange for secure component access
- No secrets in code or configuration files

## Scalability

### Horizontal Scaling
- Deploy to multiple edge devices via thing groups
- Centralized component management

### Vertical Scaling
- Configurable EC2 instance types
- Model size adjustable based on hardware

## Network Resilience

- Local MQTT broker for offline operation
- Buffered message queuing
- Automatic reconnection to cloud
- Local data persistence in InfluxDB