# Deployment Options

This project supports **2 simplified deployment options**, both using the **same component code** without duplication.

## 🏗️ **Architecture: No Code Duplication**

Following frugal architecture principles, we have **zero code duplication**:

```
components/                    # Single source of truth
├── sensor-simulator/         # Sensor data generation
├── llm-inference/            # LLM analysis engine  
├── chatbot-ui/              # Web interface
└── telemetry-bridge/        # Data forwarding

# Used by BOTH deployment options:
# ✅ AWS Greengrass (production)
# ✅ Local Greengrass Container (development/testing)
```

## 🚀 **Deployment Options**

### 1. **AWS Greengrass (Production)**
Complete cloud-managed edge deployment with EC2.

```bash
cd pipeline
chmod +x deploy-v2.sh
./deploy-v2.sh
```

**Access:**
- Grafana: `http://<EC2_IP>:3000` 
- ChatBot: `http://<EC2_IP>:8080`

**Features:**
- Terraform infrastructure automation
- Official AWS Greengrass Labs components
- Auto-scaling and fleet management
- CloudWatch integration

---

### 2. **Local Greengrass Container (Development/Testing)**
Complete Greengrass runtime locally with component management.

```bash
./run-local.sh
```

**Access:**
- Grafana: http://localhost:3000
- ChatBot: http://localhost:8080
- Component Server: http://localhost:8090/components/

**Features:**
- ✅ **Uses existing component code directly**
- True Greengrass component lifecycle
- Component versioning and updates
- Official AWS components (InfluxDB/Grafana)
- Identical to AWS environment

## 📊 **Comparison Matrix**

| Feature | Local Greengrass | AWS Greengrass |
|---------|------------------|----------------|
| **Setup Time** | 2 minutes | 15 minutes |
| **AWS Costs** | $0 | ~$50/month |
| **Component Lifecycle** | ✅ Full | ✅ Full |
| **Official AWS Components** | ✅ | ✅ |
| **Fleet Management** | ❌ | ✅ |
| **Development Speed** | ✅ Fast | Slow |
| **Production Parity** | ✅ High | ✅ Perfect |

## 🎯 **Recommended Usage**

### **Development Workflow**
1. **Development/Testing**: Use `./run-local.sh` for Greengrass lifecycle testing
2. **Production Deployment**: Use `./deploy-v2.sh` for AWS deployment

### **Demo Scenarios**
- **Development Demo**: Local Greengrass (shows true Greengrass capabilities)
- **Customer Demo**: AWS Greengrass (production environment)

## 🛠️ **All Features Available in Both Options**

### ✅ **1. Dummy Sensor Data Generation**
- 5 sensors per type (temperature, pressure, vibration)
- Configurable anomaly injection
- Realistic time-based patterns

### ✅ **2. InfluxDB Storage** 
- Time-series data with proper tagging
- Automatic bucket setup and configuration
- Data retention and querying

### ✅ **3. Grafana Dashboards**
- Real-time sensor visualization  
- Anomaly detection charts
- System health indicators
- Auto-refresh every 5 seconds

### ✅ **4. ChatBot Web UI**
- Natural language sensor queries
- Real-time WebSocket communication
- Context-aware LLM responses

### ✅ **5. Advanced ChatBot Capabilities**

#### **List Available Sensors**
```
User: "List all available sensors"
Bot: "I'm monitoring 15 sensors: 5 temperature, 5 pressure, 5 vibration sensors across 3 zones."
```

#### **Fetch Sensor Data from InfluxDB**
```  
User: "Show me temperature readings"
Bot: "🌡️ Current temperature: 45.2°C in zone_1. Based on 12 recent readings."
```

#### **Analyze Anomalies with Custom Criteria**
```
User: "Alert when temperature exceeds 65°C"
Bot: "✅ I'll monitor for temperature > 65°C. Current max is 62.1°C - within limits."

User: "Are there any pressure anomalies?"
Bot: "⚠️ Detected 2 pressure anomalies: eq_102 exceeded 195kPa threshold."
```

## 🔧 **Configuration Management**

All deployment options use the **same configuration patterns**:

### **Environment Variables**
```bash
# Sensor Configuration  
SENSOR_COUNT=5
SAMPLING_INTERVAL_MS=5000
ANOMALY_PROBABILITY=0.05

# LLM Configuration
MODEL_NAME=TinyLlama-1.1B-Chat
TEMPERATURE=0.7
BATCH_SIZE=10

# ChatBot Configuration
WEB_PORT=8080
DEBUG_MODE=true
```

### **Component Configuration**
- Local Greengrass: `docker/greengrass/config/config.yaml`
- AWS Greengrass: Terraform deployment configuration

## 🏆 **Code Exterminator Results**

**✅ Zero Duplication Achieved:**
- **Simplified**: From 3 deployment options to 2 focused options
- **Removed**: Standalone Docker Compose option to eliminate complexity
- **Reused**: 100% of component code across both deployment options
- **Maintained**: All functionality with cleaner, simpler architecture

This approach perfectly embodies the frugal architecture principles: **build once, deploy anywhere, maintain simply**.