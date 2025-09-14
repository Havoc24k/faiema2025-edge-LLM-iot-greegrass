#!/usr/bin/env python3

import json
import time
import random
import requests
from datetime import datetime

def generate_sensor_data():
    sensors = {}

    # Generate temperature sensors
    for i in range(3):
        is_anomaly = random.random() < 0.1
        temp = random.uniform(20, 80)
        if is_anomaly:
            temp = random.uniform(90, 120)

        sensors[f'temperature_{i}'] = {
            'type': 'temperature',
            'value': round(temp, 2),
            'unit': 'celsius',
            'is_anomaly': is_anomaly,
            'timestamp': datetime.utcnow().isoformat()
        }

    # Generate pressure sensors
    for i in range(2):
        is_anomaly = random.random() < 0.1
        pressure = random.uniform(100, 200)
        if is_anomaly:
            pressure = random.uniform(250, 300)

        sensors[f'pressure_{i}'] = {
            'type': 'pressure',
            'value': round(pressure, 2),
            'unit': 'kPa',
            'is_anomaly': is_anomaly,
            'timestamp': datetime.utcnow().isoformat()
        }

    # Generate vibration sensors
    for i in range(2):
        is_anomaly = random.random() < 0.1
        vibration = random.uniform(0, 10)
        if is_anomaly:
            vibration = random.uniform(15, 25)

        sensors[f'vibration_{i}'] = {
            'type': 'vibration',
            'value': round(vibration, 2),
            'unit': 'mm/s',
            'is_anomaly': is_anomaly,
            'timestamp': datetime.utcnow().isoformat()
        }

    return sensors

def write_to_influxdb(sensor_data):
    try:
        # Write to InfluxDB
        lines = []
        for sensor_id, data in sensor_data.items():
            line = f"sensor_data,sensor_id={sensor_id},sensor_type={data['type']} value={data['value']},is_anomaly={data['is_anomaly']},unit=\"{data['unit']}\" {int(datetime.now().timestamp() * 1000000000)}"
            lines.append(line)

        payload = "\n".join(lines)
        response = requests.post(
            "http://influxdb:8086/write?db=sensors",
            data=payload,
            headers={'Content-Type': 'application/octet-stream'},
            timeout=5
        )
        print(f"Written {len(sensor_data)} sensor readings to InfluxDB")
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

def main():
    print("Starting simple sensor data generator...")
    while True:
        sensor_data = generate_sensor_data()
        write_to_influxdb(sensor_data)
        time.sleep(5)

if __name__ == '__main__':
    main()