#!/usr/bin/env python3

import time
import requests
import sys
import os

# Add shared utilities to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from sensor_utils import SensorDataGenerator

def write_to_influxdb(sensor_data):
    """Write sensor data to InfluxDB using line protocol"""
    try:
        lines = []
        for sensor_id, data in sensor_data.items():
            line = f"sensor_data,sensor_id={sensor_id},sensor_type={data['type']},equipment_id=edge_device_01,location=production_floor value={data['value']},is_anomaly={data['is_anomaly']} {data['timestamp'] * 1_000_000}"
            lines.append(line)

        response = requests.post(
            "http://localhost:8086/write?db=sensors",
            data="\n".join(lines),
            headers={'Content-Type': 'application/octet-stream'},
            timeout=5
        )
        print(f"Written {len(sensor_data)} sensor readings to InfluxDB")
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

def main():
    """Main sensor generation loop"""
    print("Starting optimized sensor data generator...")
    while True:
        sensor_data = SensorDataGenerator.generate_sensor_set(anomaly_rate=0.1)
        write_to_influxdb(sensor_data)
        time.sleep(5)

if __name__ == '__main__':
    main()