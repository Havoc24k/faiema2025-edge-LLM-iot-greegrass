#!/usr/bin/env python3

import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import PublishToTopicRequest, PublishMessage, BinaryMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorSimulator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ipc_client = awsiot.greengrasscoreipc.connect()
        self.sensor_count = config.get('sensorCount', 5)
        self.sampling_interval = config.get('samplingIntervalMs', 5000) / 1000
        self.anomaly_probability = config.get('anomalyProbability', 0.05)
        self.sensors_config = config.get('sensors', {})
        
    def generate_sensor_reading(self, sensor_type: str, sensor_id: int) -> Dict[str, Any]:
        """Generate a single sensor reading with potential anomalies"""
        config = self.sensors_config.get(sensor_type, {})
        min_val = config.get('min', 0)
        max_val = config.get('max', 100)
        unit = config.get('unit', '')
        
        # Normal reading
        value = random.uniform(min_val, max_val)
        
        # Inject anomaly based on probability
        is_anomaly = random.random() < self.anomaly_probability
        if is_anomaly:
            # Generate anomaly value (outside normal range)
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
            'is_anomaly': is_anomaly
        }
    
    def publish_reading(self, reading: Dict[str, Any]):
        """Publish sensor reading to IoT Core topic"""
        topic = f"industrial/sensors/{reading['sensor_id']}"
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
            
            logger.info(f"Published to {topic}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
    
    def run(self):
        """Main simulation loop"""
        logger.info("Starting sensor simulator")
        
        while True:
            try:
                # Generate readings for all sensors
                for sensor_type in self.sensors_config.keys():
                    for i in range(self.sensor_count):
                        reading = self.generate_sensor_reading(sensor_type, i)
                        self.publish_reading(reading)
                        
                        # Also publish to local topic for Grafana
                        local_topic = f"local/sensors/{reading['sensor_id']}"
                        self.publish_to_local_topic(local_topic, reading)
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(5)
    
    def publish_to_local_topic(self, topic: str, data: Dict[str, Any]):
        """Publish to local topic for inter-component communication"""
        try:
            request = PublishToTopicRequest()
            request.topic = topic
            publish_message = PublishMessage()
            publish_message.binary_message = BinaryMessage()
            publish_message.binary_message.message = json.dumps(data).encode('utf-8')
            request.publish_message = publish_message
            
            operation = self.ipc_client.new_publish_to_topic()
            operation.activate(request)
            future = operation.get_response()
            future.result(timeout=5.0)
            
        except Exception as e:
            logger.error(f"Failed to publish to local topic: {e}")

def main():
    # Load configuration from Greengrass
    try:
        with open('/greengrass/v2/work/com.edge.llm.SensorSimulator/config.json', 'r') as f:
            config = json.load(f)
    except:
        # Use default configuration if not available
        config = {
            'sensorCount': 5,
            'samplingIntervalMs': 5000,
            'anomalyProbability': 0.05,
            'sensors': {
                'temperature': {'min': 20, 'max': 80, 'unit': 'celsius'},
                'pressure': {'min': 100, 'max': 200, 'unit': 'kPa'},
                'vibration': {'min': 0, 'max': 10, 'unit': 'mm/s'}
            }
        }
    
    simulator = SensorSimulator(config)
    simulator.run()

if __name__ == '__main__':
    main()