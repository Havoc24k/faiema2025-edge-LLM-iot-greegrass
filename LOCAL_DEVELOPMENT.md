# Local Development Setup

This setup allows you to run the entire Edge LLM IoT system locally using Docker, with **AWS IoT Greengrass running as a container** and deploying your existing components.

## 🎯 **Benefits of This Approach**

- **✅ Reuse Existing Code**: No code duplication - uses the same components as AWS deployment
- **✅ True Greengrass Runtime**: Identical to production environment
- **✅ Component Lifecycle**: Proper Greengrass component management and monitoring
- **✅ Easy Development**: Fast iteration without AWS dependencies
- **✅ Cost Efficient**: No AWS charges during development

## 🚀 **Quick Start**

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available for containers
- Ports 3000, 8080, 8086, 8090 available

### Start Local Environment
```bash
# Make scripts executable
chmod +x run-local.sh update-recipes-local.sh

# Start the complete system
./run-local.sh
```

### Access Applications
- **🤖 ChatBot Web UI**: http://localhost:8080
- **📊 Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **📈 InfluxDB UI**: http://localhost:8086 (admin/admin123)
- **🔧 Component Server**: http://localhost:8090/components/

## 📋 **What You Can Do**

### 1. **Generate Dummy Sensor Data** ✅
- 5 sensors per type (temperature, pressure, vibration)
- Realistic time-based variations and patterns
- Configurable anomaly injection (5% probability)
- Data published every 5 seconds

### 2. **Store Data in InfluxDB** ✅
- Time-series database with automatic setup
- Organized by sensor type, location, equipment
- Data retention and querying capabilities
- Pre-configured for Grafana integration

### 3. **Visualize in Grafana Dashboard** ✅
- Real-time sensor readings charts
- Anomaly detection visualizations
- System health indicators
- Auto-refreshing every 5 seconds

### 4. **Interactive ChatBot Web UI** ✅
- Natural language interface for sensor queries
- Real-time WebSocket communication
- Context-aware responses using current sensor data

### 5. **Advanced ChatBot Capabilities** ✅

#### **a. List All Available Sensors**
```
User: "List all available sensors"
Bot: "I'm monitoring 15 sensors across 3 types:
• Temperature sensors (5): temperature_0 to temperature_4
• Pressure sensors (5): pressure_0 to pressure_4  
• Vibration sensors (5): vibration_0 to vibration_4
All sensors are active and reporting data every 5 seconds."
```

#### **b. Fetch Data from InfluxDB**
```
User: "Show me temperature readings"
Bot: "🌡️ Current temperature reading: 45.2°C. Based on 12 recent readings."

User: "What's the pressure in zone 2?"  
Bot: "📊 Current pressure reading: 156.7kPa. Based on 8 recent readings."
```

#### **c. Analyze and Detect Anomalies**
```
User: "Are there any anomalies detected?"
Bot: "⚠️ I've detected 3 anomalies in recent sensor readings. Temperature sensor exceeded 75°C threshold. This could indicate equipment overheating."

User: "Define custom anomaly criteria"
Bot: "I can monitor for: temperature > 70°C, pressure > 190kPa, vibration > 8mm/s. Would you like to adjust these thresholds?"
```

#### **d. User-Defined Criteria**
The ChatBot can handle custom analysis requests:
```
User: "Alert me when temperature exceeds 65°C"
User: "Show trends for the last 30 minutes"
User: "Compare current readings to yesterday"
User: "Which zone has the most anomalies?"
```

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Environment               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │            AWS IoT Greengrass Container              │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │              Greengrass Components              │ │   │
│  │  │  • Sensor Simulator                             │ │   │
│  │  │  • LLM Inference Engine                         │ │   │
│  │  │  • ChatBot Web UI                               │ │   │
│  │  │  • Telemetry Bridge                             │ │   │
│  │  │  • Official InfluxDB/Grafana Components        │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │   InfluxDB  │  │   Grafana   │  │ Component Server│     │
│  │   :8086     │  │    :3000    │  │      :8090      │     │
│  └─────────────┘  └─────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ **Development Commands**

### Container Management
```bash
# View all containers
docker-compose -f docker-compose-greengrass.yml ps

# View logs
docker-compose -f docker-compose-greengrass.yml logs -f greengrass-core
docker-compose -f docker-compose-greengrass.yml logs -f grafana

# Restart specific service
docker-compose -f docker-compose-greengrass.yml restart greengrass-core

# Stop everything
docker-compose -f docker-compose-greengrass.yml down

# Clean up (removes volumes)
docker-compose -f docker-compose-greengrass.yml down -v
```

### Component Development
```bash
# Update component and redeploy
# 1. Modify your component code
# 2. Components are auto-reloaded by Greengrass

# Browse component artifacts
curl http://localhost:8090/components/

# Check Greengrass status
docker exec greengrass-local grep -r "component" /greengrass/v2/logs/
```

### Data Inspection
```bash
# Query InfluxDB directly
curl -X POST "http://localhost:8086/api/v2/query" \
  -H "Authorization: Token edge-llm-token-12345" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"sensors") |> range(start: -1h) |> limit(n:10)'

# Monitor MQTT messages
docker exec greengrass-local mosquitto_sub -h localhost -t "local/sensors/+"
```

## 🔧 **Configuration**

### Environment Variables
Component behavior can be customized via environment variables in `docker-compose-greengrass.yml`:

```yaml
# Sensor Simulator
- SENSOR_COUNT=5
- SAMPLING_INTERVAL_MS=5000
- ANOMALY_PROBABILITY=0.05

# LLM Inference  
- MODEL_NAME=TinyLlama-1.1B-Chat
- MAX_TOKENS=100
- TEMPERATURE=0.7

# ChatBot UI
- WEB_PORT=8080
- DEBUG_MODE=true
```

### Component Configuration
Individual components can be configured via their recipe files or the Greengrass config in `docker/greengrass/config/config.yaml`.

## 🚨 **Troubleshooting**

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find what's using the port
   lsof -i :3000
   # Kill the process or change port in docker-compose.yml
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose -f docker-compose-greengrass.yml logs greengrass-core
   # Often due to insufficient memory or permissions
   ```

3. **No Data in Grafana**
   ```bash
   # Check if InfluxDB is receiving data
   docker exec greengrass-local influx query 'from(bucket:"sensors") |> range(start: -1h) |> limit(n:10)'
   ```

4. **Components Not Loading**
   ```bash
   # Verify component server is accessible
   curl http://localhost:8090/components/
   # Check Greengrass component logs
   docker exec greengrass-local find /greengrass/v2/logs -name "*.log" -exec tail -f {} +
   ```

### Performance Tuning

- **Memory**: Increase Docker memory limit to 6-8GB for full LLM inference
- **CPU**: LLM inference benefits from more CPU cores
- **Disk**: Ensure sufficient space for InfluxDB data and model files

## 🔄 **Development Workflow**

1. **Start Local Environment**: `./run-local.sh`
2. **Develop Components**: Edit files in `components/`
3. **Test Changes**: Components auto-reload in Greengrass
4. **View Results**: Use Grafana dashboard and ChatBot UI
5. **Debug Issues**: Check logs and component status
6. **Deploy to AWS**: Use existing `deploy-v2.sh` script

This setup provides the complete Edge LLM IoT experience locally, with all the capabilities you requested for the demo!