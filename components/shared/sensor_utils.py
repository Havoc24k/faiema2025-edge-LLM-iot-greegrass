#!/usr/bin/env python3

import time
import random
from typing import Dict, Any, List


class SensorDataGenerator:
    """Maritime vessel sensor data generation utility"""

    # Maritime sensor configurations by area and type
    SENSOR_CONFIGS = {
        # Engine Room Sensors
        'engine_cylinder_temp': {'min': 300, 'max': 450, 'unit': 'celsius', 'anomaly_range': (500, 600)},
        'oil_pressure': {'min': 300, 'max': 500, 'unit': 'kPa', 'anomaly_range': (100, 200)},  # Low pressure = anomaly
        'oil_temperature': {'min': 60, 'max': 90, 'unit': 'celsius', 'anomaly_range': (110, 140)},
        'fuel_flow_rate': {'min': 50, 'max': 200, 'unit': 'L/h', 'anomaly_range': (250, 400)},
        'fuel_pressure': {'min': 200, 'max': 400, 'unit': 'kPa', 'anomaly_range': (50, 150)},
        'vibration_main': {'min': 0, 'max': 8, 'unit': 'mm/s', 'anomaly_range': (15, 25)},
        'shaft_torque': {'min': 8000, 'max': 12000, 'unit': 'Nm', 'anomaly_range': (15000, 20000)},
        'shaft_rpm': {'min': 100, 'max': 150, 'unit': 'rpm', 'anomaly_range': (200, 250)},
        'bilge_level': {'min': 0, 'max': 50, 'unit': 'mm', 'anomaly_range': (200, 500)},

        # Cargo Hold Sensors
        'cargo_temperature': {'min': -5, 'max': 25, 'unit': 'celsius', 'anomaly_range': (35, 50)},
        'cargo_humidity': {'min': 40, 'max': 80, 'unit': '%RH', 'anomaly_range': (90, 95)},
        'o2_level': {'min': 19.5, 'max': 21, 'unit': '%', 'anomaly_range': (15, 18)},  # Low O2 = danger
        'co2_level': {'min': 300, 'max': 800, 'unit': 'ppm', 'anomaly_range': (5000, 10000)},
        'ch4_level': {'min': 0, 'max': 10, 'unit': 'ppm', 'anomaly_range': (50, 100)},
        'cargo_weight': {'min': 500, 'max': 2000, 'unit': 'tonnes', 'anomaly_range': (2500, 3000)},
        'motion_sensor': {'min': 0, 'max': 0.5, 'unit': 'g', 'anomaly_range': (1.5, 3.0)},
        'water_ingress': {'min': 0, 'max': 5, 'unit': 'mm', 'anomaly_range': (50, 200)},

        # Safety Sensors (Boolean-like but with thresholds)
        'fire_detector': {'min': 0, 'max': 5, 'unit': 'level', 'anomaly_range': (8, 10)},
        'smoke_detector': {'min': 0, 'max': 3, 'unit': 'level', 'anomaly_range': (7, 10)}
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
        """Generate complete maritime vessel sensor set"""
        sensors = {}

        # Engine Room Sensors
        engine_sensors = [
            ('engine_cylinder_temp', 4),  # 4 cylinder temperature sensors
            ('oil_pressure', 2),          # Main and auxiliary oil pressure
            ('oil_temperature', 1),       # Oil temperature
            ('fuel_flow_rate', 2),        # Main and backup fuel flow
            ('fuel_pressure', 1),         # Fuel pressure
            ('vibration_main', 3),        # Main engine vibration sensors
            ('shaft_torque', 1),          # Propeller shaft torque
            ('shaft_rpm', 1),             # Shaft RPM
            ('bilge_level', 2)            # Bilge water level sensors
        ]

        # Cargo Hold Sensors
        cargo_sensors = [
            ('cargo_temperature', 6),     # Temperature in 6 holds
            ('cargo_humidity', 6),        # Humidity in 6 holds
            ('o2_level', 3),              # O2 levels in holds
            ('co2_level', 3),             # CO2 levels
            ('ch4_level', 3),             # Methane detection
            ('cargo_weight', 6),          # Weight sensors per hold
            ('motion_sensor', 4),         # Cargo movement detection
            ('water_ingress', 6)          # Water ingress sensors
        ]

        # Safety Sensors
        safety_sensors = [
            ('fire_detector', 8),         # Fire detectors throughout vessel
            ('smoke_detector', 8)         # Smoke detectors
        ]

        # Generate all sensor types
        all_sensors = engine_sensors + cargo_sensors + safety_sensors

        for sensor_type, count in all_sensors:
            for i in range(count):
                sensor_id = f'{sensor_type}_{i+1:02d}'  # e.g., engine_cylinder_temp_01
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
                    'vessel_id': 'MV_FAIEMA_2025',
                    'location': cls._get_sensor_location(data['type'])
                },
                'fields': {
                    'value': data['value'],
                    'is_anomaly': data['is_anomaly']
                },
                'time': data['timestamp']
            }
            for data in sensors.values()
        ]

    @classmethod
    def _get_sensor_location(cls, sensor_type: str) -> str:
        """Map sensor type to vessel location"""
        engine_room_sensors = [
            'engine_cylinder_temp', 'oil_pressure', 'oil_temperature',
            'fuel_flow_rate', 'fuel_pressure', 'vibration_main',
            'shaft_torque', 'shaft_rpm', 'bilge_level'
        ]

        cargo_sensors = [
            'cargo_temperature', 'cargo_humidity', 'o2_level',
            'co2_level', 'ch4_level', 'cargo_weight',
            'motion_sensor', 'water_ingress'
        ]

        safety_sensors = ['fire_detector', 'smoke_detector']

        if sensor_type in engine_room_sensors:
            return 'engine_room'
        elif sensor_type in cargo_sensors:
            return 'cargo_hold'
        elif sensor_type in safety_sensors:
            return 'general'
        else:
            return 'unknown'