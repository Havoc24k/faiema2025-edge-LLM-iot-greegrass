#!/usr/bin/env python3

import json
import time
import random
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Try Greengrass IPC first, fallback to MQTT
try:
    import awsiot.greengrasscoreipc
    from awsiot.greengrasscoreipc.model import (
        PublishToTopicRequest,
        PublishMessage,
        BinaryMessage
    )
    GREENGRASS_AVAILABLE = True
except ImportError:
    GREENGRASS_AVAILABLE = False
    import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorSimulator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.sensor_count = self.config.get('sensorCount', int(os.getenv('SENSOR_COUNT', '5')))
        self.sampling_interval = self.config.get('samplingIntervalMs', int(os.getenv('SAMPLING_INTERVAL_MS', '5000'))) / 1000
        self.anomaly_probability = self.config.get('anomalyProbability', float(os.getenv('ANOMALY_PROBABILITY', '0.05')))
        
        # Sensor configurations
        self.sensors_config = {
            'temperature': {'min': 20, 'max': 80, 'unit': '°C'},
            'pressure': {'min': 100, 'max': 200, 'unit': 'kPa'},
            'vibration': {'min': 0, 'max': 10, 'unit': 'mm/s'}
        }
        
        # Setup communication
        if GREENGRASS_AVAILABLE:
            try:
                self.ipc_client = awsiot.greengrasscoreipc.connect()
                self.use_greengrass = True
                logger.info("Using Greengrass IPC communication")
            except:
                self.use_greengrass = False
                self.setup_mqtt_client()
        else:
            self.use_greengrass = False
            self.setup_mqtt_client()
    
    def setup_mqtt_client(self):
        """Setup MQTT client for local development"""
        logger.info("Using MQTT communication")
        self.mqtt_client = mqtt.Client(client_id="sensor-simulator")
        self.mqtt_client.on_connect = self.on_mqtt_connect
        
        mqtt_host = os.getenv('MQTT_BROKER', 'localhost')
        mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        
        try:
            self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT client connected successfully")
        else:
            logger.error(f"MQTT connection failed: {rc}")
    
    def generate_sensor_reading(self, sensor_type: str, sensor_id: int) -> Dict[str, Any]:
        """Generate a single sensor reading with potential anomalies"""
        import math
        
        config = self.sensors_config.get(sensor_type, {})
        min_val = config.get('min', 0)
        max_val = config.get('max', 100)
        unit = config.get('unit', '')
        
        # Normal reading with realistic variation
        base_value = random.uniform(min_val, max_val)
        
        # Add time-based variation patterns
        time_factor = time.time() % 3600  # Hour cycle
        if sensor_type == 'temperature':
            base_value += 5 * math.sin(time_factor / 600)  # 10-minute cycle
        elif sensor_type == 'pressure':
            base_value += 10 * math.sin(time_factor / 1800)  # 30-minute cycle
        elif sensor_type == 'vibration':
            base_value += random.uniform(-2, 2)
        
        value = max(min_val * 0.5, min(max_val * 1.5, base_value))
        
        # Inject anomaly based on probability
        is_anomaly = random.random() < self.anomaly_probability
        if is_anomaly:
            if random.random() < 0.5:
                value = max_val * random.uniform(1.1, 1.5)
            else:
                value = min_val * random.uniform(0.5, 0.9)
        
        return {
            'sensor_id': f'{sensor_type}_{sensor_id}',
            'type': sensor_type,
            'value': round(value, 2),
            'unit': unit,
            'timestamp': datetime.utcnow().isoformat(),
            'is_anomaly': is_anomaly,
            'location': f'zone_{(sensor_id % 3) + 1}',
            'equipment_id': f'eq_{sensor_id + 100}'
        }
    
    def publish_reading(self, reading: Dict[str, Any]):
        """Publish sensor reading"""
        if self.use_greengrass:
            self.publish_to_greengrass(reading)
        else:
            self.publish_to_mqtt(reading)
    
    def publish_to_greengrass(self, reading: Dict[str, Any]):
        """Publish using Greengrass IPC"""
        topic = f"local/sensors/{reading['sensor_id']}"
        message = json.dumps(reading)
        
        try:
            request = PublishToTopicRequest()
            request.topic = topic
            publish_message = PublishMessage()
            publish_message.binary_message = BinaryMessage()
            publish_message.binary_message.message = message.encode('utf-8')
            request.publish_message = publish_message
            
            operation = self.ipc_client.new_publish_to_topic()
            operation.activate(request)
            future = operation.get_response()
            future.result(timeout=5.0)
            
            logger.debug(f"Published to Greengrass topic {topic}")
        except Exception as e:
            logger.error(f"Failed to publish to Greengrass: {e}")
    
    def publish_to_mqtt(self, reading: Dict[str, Any]):
        """Publish using MQTT client"""
        topic = f"local/sensors/{reading['sensor_id']}"
        message = json.dumps(reading)
        
        try:
            result = self.mqtt_client.publish(topic, message, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to MQTT topic {topic}")
            else:
                logger.error(f"MQTT publish failed: {result.rc}")
        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")
    
    def run(self):
        """Main simulation loop"""
        logger.info("Starting sensor simulator")
        logger.info(f"Mode: {'Greengrass IPC' if self.use_greengrass else 'MQTT'}")
        logger.info(f"Sensors: {list(self.sensors_config.keys())}")
        logger.info(f"Count per type: {self.sensor_count}")
        logger.info(f"Sampling interval: {self.sampling_interval}s")
        logger.info(f"Anomaly probability: {self.anomaly_probability}")
        
        while True:
            try:
                # Generate readings for all sensors
                for sensor_type in self.sensors_config.keys():
                    for i in range(self.sensor_count):
                        reading = self.generate_sensor_reading(sensor_type, i)
                        self.publish_reading(reading)
                        
                        if reading['is_anomaly']:
                            logger.warning(f"Anomaly generated: {reading['sensor_id']} = {reading['value']}{reading['unit']}")
                
                time.sleep(self.sampling_interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping sensor simulator")
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(5)
        
        # Cleanup
        if not self.use_greengrass and hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    # Load configuration from file or environment
    config = {}
    try:
        config_path = '/greengrass/v2/work/com.edge.llm.SensorSimulator/config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            logger.info("Using default configuration (local development mode)")
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")
    
    simulator = SensorSimulator(config)
    simulator.run()

if __name__ == '__main__':
    main()