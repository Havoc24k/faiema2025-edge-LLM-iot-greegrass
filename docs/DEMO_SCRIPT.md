# Demo Script

## Introduction (2 minutes)

"Today we're demonstrating edge-native LLM inference for industrial IoT environments using AWS IoT Greengrass and frugal architecture principles. This solution showcases how to build cost-effective, efficient edge AI systems by leveraging official AWS components and avoiding unnecessary complexity."

### Key Benefits
- **Reduced Latency**: Local inference in milliseconds vs seconds for cloud
- **Improved Reliability**: Operates offline without internet connectivity  
- **Enhanced Security**: Sensitive data never leaves the facility
- **Cost Efficiency**: 90% cost reduction vs cloud APIs
- **Frugal Design**: Uses proven components, eliminates code duplication

## Architecture Overview (3 minutes)

Show architecture diagram and explain:

1. **Edge Device** (EC2 for demo, but works on Raspberry Pi/Jetson)
   - AWS IoT Greengrass Core runtime
   - Docker for containerized services
   - Local MQTT broker

2. **Components**
   - **Custom**: Sensor Simulator, LLM Inference Engine, ChatBot Web UI, Telemetry Bridge
   - **Official AWS**: InfluxDBGrafana, InfluxDBPublisher (battle-tested)
   - **Frugal Principle**: Build custom only where you add unique value

3. **Data Flow**
   - Sensors → LLM Analysis → ChatBot + Grafana Visualization
   - Interactive chat interface for real-time queries
   - Real-time dashboards with minimal custom code

## Live Demo (15 minutes)

### 1. Show Grafana Dashboard
Navigate to `http://<EC2_IP>:3000`

- Point out real-time sensor readings
- Show normal operating ranges
- Explain the different sensor types
- Highlight automated anomaly detection

### 2. Interactive ChatBot Demo
Navigate to `http://<EC2_IP>:8080`

**Demonstrate conversational AI capabilities:**

1. **System Status Query**
   - Type: "What is the current system status?"
   - Show real-time sensor data integration
   - Point out contextual awareness

2. **Specific Sensor Queries**
   - "Show me temperature readings"
   - "Are there any pressure anomalies?"
   - "Explain the vibration levels"

3. **Predictive Insights**
   - "Should I be concerned about anything?"
   - "What maintenance actions do you recommend?"
   - "Compare current vs historical trends"

**Key Features to Highlight:**
- Real-time sensor data integration
- Natural language processing at the edge
- Instant responses without cloud latency
- Contextual awareness of current conditions

### 3. Trigger Anomaly Detection
SSH to EC2 and modify sensor simulator config:

```bash
ssh ec2-user@<EC2_IP>
sudo nano /greengrass/v2/work/com.edge.llm.SensorSimulator/config.json
# Increase anomalyProbability to 0.5
sudo systemctl restart greengrass
```

- Watch anomalies appear in dashboard
- Show LLM analysis results
- **Ask ChatBot**: "I see anomalies in the dashboard, what's happening?"
- Show contextual response with specific details
- Highlight immediate detection without cloud

### 4. Demonstrate Offline Operation
Simulate network disconnection:

```bash
sudo iptables -A OUTPUT -d 52.0.0.0/8 -j DROP  # Block AWS
```

- System continues operating
- Local inference still works
- **ChatBot remains responsive** - ask "Are you still working offline?"
- Data buffered for later sync

Restore connection:
```bash
sudo iptables -D OUTPUT -d 52.0.0.0/8 -j DROP
```

### 5. Show Component Logs
Display real-time processing:

```bash
# Show LLM processing
sudo tail -f /greengrass/v2/logs/com.edge.llm.InferenceEngine.log

# Show ChatBot interactions
sudo tail -f /greengrass/v2/logs/com.edge.llm.ChatBotUI.log
```

- Point out inference times
- Show memory usage
- Highlight chat request processing
- Demonstrate real-time component communication

## Cost Analysis (3 minutes)

### Traditional Cloud Approach
- 5 sensors × 12 readings/hour × 24 hours = 1,440 API calls/day
- At $0.001 per call = $1.44/day or $525/year per device
- 100 devices = $52,500/year

### Edge LLM Approach
- One-time EC2 cost: ~$50/month
- No API calls, minimal data transfer
- 100 devices = $5,000/year
- **90% cost reduction**

## Deployment Options (2 minutes)

### Development
- EC2 t3.medium for testing
- Docker-based components
- Manual deployment via scripts

### Production
- NVIDIA Jetson for real edge devices
- Kubernetes orchestration
- CI/CD pipeline integration
- Fleet management via AWS IoT Device Management

## Q&A Talking Points

### "How does it handle model updates?"
- Greengrass components support versioning
- Rolling updates without downtime
- A/B testing capabilities

### "What about larger models?"
- Scales with hardware (GPU support)
- Model quantization techniques
- Distributed inference possible

### "Integration with existing systems?"
- MQTT/HTTP protocols
- REST API endpoints for ChatBot
- OPC-UA adapter available
- Natural language interface reduces training needs

### "Security concerns?"
- End-to-end encryption
- Certificate-based authentication
- No data leaves premises

## Conclusion (2 minutes)

"This demo shows how edge-native LLM inference with conversational AI transforms industrial IoT:

**Technical Achievements:**
- Real-time LLM inference without cloud dependency
- Interactive ChatBot for natural language queries
- 90% cost reduction vs cloud APIs
- Enhanced reliability and security

**Business Impact:**
- Reduced operator training - ask questions in plain English
- Faster troubleshooting with contextual AI assistance
- Immediate insights without connectivity concerns
- Simple deployment with AWS Greengrass

**Scalability:**
- Same architecture from proof-of-concept to production
- Scale from one device to thousands
- Add new sensor types without code changes
- Natural language interface adapts automatically

The combination of Grafana dashboards for technical users and ChatBot for conversational queries provides comprehensive edge AI capabilities."

## Follow-up Resources
- GitHub repository with full code
- AWS Greengrass documentation
- TinyLlama model details
- Cost calculator spreadsheet