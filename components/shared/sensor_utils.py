#!/usr/bin/env python3

import time
import random
from typing import Dict, Any, List


class SensorDataGenerator:
    """Unified sensor data generation utility for IoT edge devices"""

    # Sensor type configurations
    SENSOR_CONFIGS = {
        'temperature': {'min': 20, 'max': 80, 'unit': 'celsius', 'anomaly_range': (90, 120)},
        'pressure': {'min': 100, 'max': 200, 'unit': 'kPa', 'anomaly_range': (250, 300)},
        'vibration': {'min': 0, 'max': 10, 'unit': 'mm/s', 'anomaly_range': (15, 25)}
    }

    @classmethod
    def generate_reading(cls, sensor_type: str, sensor_id: str, anomaly_rate: float = 0.1) -> Dict[str, Any]:
        """Generate a single sensor reading with configurable anomaly injection"""
        config = cls.SENSOR_CONFIGS.get(sensor_type, {'min': 0, 'max': 100, 'unit': '', 'anomaly_range': (150, 200)})

        is_anomaly = random.random() < anomaly_rate

        if is_anomaly:
            value = random.uniform(*config['anomaly_range'])
        else:
            value = random.uniform(config['min'], config['max'])

        return {
            'sensor_id': sensor_id,
            'type': sensor_type,
            'value': round(value, 2),
            'unit': config['unit'],
            'is_anomaly': is_anomaly,
            'timestamp': time.time_ns() // 1_000_000  # milliseconds since epoch
        }

    @classmethod
    def generate_sensor_set(cls, anomaly_rate: float = 0.1) -> Dict[str, Dict[str, Any]]:
        """Generate complete sensor set (3 temp, 2 pressure, 2 vibration)"""
        sensors = {}

        # Generate all sensor types with counts
        sensor_specs = [
            ('temperature', 3),
            ('pressure', 2),
            ('vibration', 2)
        ]

        for sensor_type, count in sensor_specs:
            for i in range(count):
                sensor_id = f'{sensor_type}_{i}'
                sensors[sensor_id] = cls.generate_reading(sensor_type, sensor_id, anomaly_rate)

        return sensors

    @classmethod
    def to_influxdb_format(cls, sensors: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert sensor data to InfluxDB line protocol format"""
        return [
            {
                'measurement': 'sensor_data',
                'tags': {
                    'sensor_id': data['sensor_id'],
                    'sensor_type': data['type'],
                    'equipment_id': 'edge_device_01',
                    'location': 'production_floor'
                },
                'fields': {
                    'value': data['value'],
                    'is_anomaly': data['is_anomaly']
                },
                'time': data['timestamp']
            }
            for data in sensors.values()
        ]