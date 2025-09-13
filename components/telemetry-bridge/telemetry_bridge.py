#!/usr/bin/env python3

import json
import logging
from datetime import datetime
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    SubscribeToTopicRequest,
    PublishToTopicRequest,
    PublishMessage,
    BinaryMessage,
    SubscriptionResponseMessage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelemetryBridge:
    """Bridge sensor and LLM data to InfluxDB via the official InfluxDBPublisher component"""
    
    def __init__(self, config):
        self.config = config
        self.ipc_client = awsiot.greengrasscoreipc.connect()
        self.sensor_topics = config.get('sensorTopics', ['local/sensors/+'])
        self.analysis_topics = config.get('analysisTopics', ['local/analysis/results'])
        
    def subscribe_to_topics(self):
        """Subscribe to sensor and analysis topics"""
        all_topics = self.sensor_topics + self.analysis_topics
        
        for topic in all_topics:
            try:
                request = SubscribeToTopicRequest()
                request.topic = topic
                
                handler = self.handle_message
                operation = self.ipc_client.new_subscribe_to_topic(handler)
                future = operation.activate(request)
                future.result(timeout=10.0)
                
                logger.info(f"Subscribed to topic: {topic}")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to {topic}: {e}")
    
    def handle_message(self, message: SubscriptionResponseMessage):
        """Transform and forward messages to InfluxDB"""
        try:
            topic = message.topic
            payload = json.loads(message.binary_message.message.decode('utf-8'))
            
            # Transform to InfluxDB telemetry format
            telemetry_data = self.transform_to_telemetry(topic, payload)
            
            # Publish to the InfluxDBPublisher topic
            self.publish_telemetry(telemetry_data)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def transform_to_telemetry(self, topic, payload):
        """Transform sensor/analysis data to InfluxDB telemetry format"""
        
        if "sensors" in topic:
            # Sensor data transformation
            return {
                "namespace": "EdgeLLM/Sensors",
                "name": payload.get("sensor_id", "unknown"),
                "unit": payload.get("unit", ""),
                "value": payload.get("value", 0),
                "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
                "metadata": {
                    "sensor_type": payload.get("type", "unknown"),
                    "is_anomaly": str(payload.get("is_anomaly", False))
                }
            }
        elif "analysis" in topic:
            # Analysis data transformation
            return {
                "namespace": "EdgeLLM/Analysis",
                "name": payload.get("type", "unknown"),
                "unit": "Count",
                "value": 1,
                "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
                "metadata": {
                    "analysis": payload.get("analysis", ""),
                    "severity": payload.get("severity", "info"),
                    "sensor_id": payload.get("sensor_id", "all")
                }
            }
        else:
            # Default transformation
            return {
                "namespace": "EdgeLLM/Unknown",
                "name": "data",
                "unit": "Count",
                "value": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": payload
            }
    
    def publish_telemetry(self, telemetry_data):
        """Publish telemetry data to InfluxDBPublisher component"""
        try:
            # The InfluxDBPublisher component listens on this topic
            topic = "$aws/things/greengrass-core-thing/greengrass/telemetry"
            
            message = json.dumps(telemetry_data)
            
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
            
            logger.debug(f"Published telemetry: {telemetry_data['namespace']}/{telemetry_data['name']}")
            
        except Exception as e:
            logger.error(f"Failed to publish telemetry: {e}")
    
    def run(self):
        """Main bridge loop"""
        logger.info("Starting telemetry bridge")
        logger.info(f"Dashboard will be available at http://<EC2_IP>:{self.config.get('dashboardPort', 3000)}")
        
        # Subscribe to topics
        self.subscribe_to_topics()
        
        # Keep running
        try:
            while True:
                import time
                time.sleep(60)
                logger.debug("Telemetry bridge running...")
        except KeyboardInterrupt:
            logger.info("Telemetry bridge stopped")

def main():
    # Load configuration
    try:
        with open('/greengrass/v2/work/com.edge.llm.TelemetryBridge/config.json', 'r') as f:
            config = json.load(f)
    except:
        # Use default configuration
        config = {
            'sensorTopics': ['local/sensors/+'],
            'analysisTopics': ['local/analysis/results'],
            'influxDBEndpoint': 'http://localhost:8086',
            'influxDBBucket': 'greengrass_telemetry',
            'dashboardPort': 3000
        }
    
    bridge = TelemetryBridge(config)
    bridge.run()

if __name__ == '__main__':
    main()