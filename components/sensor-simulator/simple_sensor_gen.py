#!/usr/bin/env python3

import time
import requests
import sys
import os

# Add shared utilities to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from sensor_utils import SensorDataGenerator

def write_to_influxdb(sensor_data):
    """Write maritime vessel sensor data to InfluxDB using line protocol"""
    try:
        lines = []
        for sensor_id, data in sensor_data.items():
            location = SensorDataGenerator._get_sensor_location(data['type'])
            line = f"sensor_data,sensor_id={sensor_id},sensor_type={data['type']},vessel_id=MV_FAIEMA_2025,location={location} value={data['value']},is_anomaly={data['is_anomaly']},unit=\"{data['unit']}\" {data['timestamp'] * 1_000_000}"
            lines.append(line)

        response = requests.post(
            "http://localhost:8086/write?db=sensors",
            data="\n".join(lines),
            headers={'Content-Type': 'application/octet-stream'},
            timeout=5
        )
        print(f"Written {len(sensor_data)} maritime sensor readings to InfluxDB")

        # Show anomaly detection summary
        anomalies = [s for s in sensor_data.values() if s['is_anomaly']]
        if anomalies:
            anomaly_list = [f"{a['sensor_id']}({a['value']}{a['unit']})" for a in anomalies[:3]]
            print(f"  - {len(anomalies)} anomalies detected: {anomaly_list}")
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

def main():
    """Main maritime vessel sensor generation loop"""
    print("Starting maritime vessel sensor data generator...")
    print("Generating data for MV FAIEMA 2025")
    print("- Engine Room: 17 sensors (temperature, pressure, vibration, torque)")
    print("- Cargo Holds: 31 sensors (environment, gas detection, weight)")
    print("- Safety Systems: 16 sensors (fire/smoke detection)")
    print("Total: 64 maritime sensors with 10% anomaly rate")

    while True:
        sensor_data = SensorDataGenerator.generate_sensor_set(anomaly_rate=0.1)
        write_to_influxdb(sensor_data)
        time.sleep(5)

if __name__ == '__main__':
    main()
