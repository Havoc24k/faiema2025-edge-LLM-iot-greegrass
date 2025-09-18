# IMMUTABLE SOFTWARE STACK CONFIGURATION

## FROZEN ARCHITECTURE - NO CHANGES ALLOWED

### Server Stack (AWS EC2 + Greengrass)
- **OS**: Amazon Linux 2023
- **Instance Type**: g4dn.xlarge (Tesla T4 GPU)
- **InfluxDB**: 1.8 (Docker container `influxdb:1.8`)
- **Grafana**: Latest stable via yum
- **AWS IoT Greengrass**: v2 latest
- **Python**: 3.9+
- **CUDA**: 12.3 + NVIDIA Driver 545

### Client Stack (ChatBot Component)
- **LLM Model**: Qwen/Qwen2.5-Coder-3B-Instruct
- **Framework**: PyTorch with CUDA 12.1
- **Web Framework**: Flask
- **Database Query Language**: InfluxQL (NOT Flux - InfluxDB 1.8 doesn't support Flux)
- **Authentication**: Token-based (edge-llm-token-12345)
- **Query Strategy**: Hardcoded maritime vessel queries with LLM analysis

### Data Stack
- **Database**: InfluxDB 1.8
  - Database: `sensors`
  - Measurement: `sensor_data`
  - Query Language: **InfluxQL ONLY**
- **Sensor Simulator**: Custom Python component generating realistic industrial sensor data
- **Data Format**: Time-series with tags (sensor_id, sensor_type) and fields (value, is_anomaly)

### Component Versions (FROZEN)
- **com.edge.llm.ChatBotUI**: v1.0.23 (Qwen2.5-Coder-3B + InfluxQL + Authentication)
- **com.edge.llm.SensorSimulator**: v1.0.5 (Maritime vessel data)
- **com.edge.llm.InfluxDB**: v1.0.0 (Docker container)
- **com.edge.llm.Grafana**: v1.0.28 (Maritime dashboard)

## CRITICAL DECISIONS - IMMUTABLE

1. **InfluxDB 1.8 with InfluxQL**: No Flux queries, only InfluxQL syntax
2. **Qwen2.5-Coder-3B**: For maritime sensor data analysis and operational limits assessment
3. **Tesla T4 GPU**: FP16 precision for memory efficiency
4. **Docker Containers**: InfluxDB and Grafana run in containers
5. **Port Allocation**: 8080 (ChatBot), 8086 (InfluxDB), 3000 (Grafana)

## QUERY SYNTAX - FIXED

### InfluxQL Query Format (ONLY THIS):
```sql
SELECT MEAN(value), MAX(value), MIN(value), COUNT(value)
FROM sensor_data
WHERE vessel_id = 'MV_FAIEMA_2025' AND time > now() - 12h
GROUP BY sensor_type
```

### NO FLUX QUERIES ALLOWED:
```
❌ from(bucket: "sensors") |> range(start: -1h)  # This will fail
```

## DEPLOYMENT CONSTRAINTS

- All code changes must be backwards compatible with this stack
- No version upgrades without explicit approval
- No database schema changes
- No additional dependencies without documentation

This configuration is now FROZEN and IMMUTABLE.