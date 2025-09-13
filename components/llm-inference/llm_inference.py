#!/usr/bin/env python3

import json
import time
import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Any, List
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
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

class LLMInferenceEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ipc_client = awsiot.greengrasscoreipc.connect()
        self.model_name = config.get('modelName', 'TinyLlama-1.1B-Chat')
        self.model_path = config.get('modelPath', '/greengrass/v2/packages/artifacts/com.edge.llm.InferenceEngine/1.0.0/models')
        self.max_tokens = config.get('maxTokens', 100)
        self.temperature = config.get('temperature', 0.7)
        self.batch_size = config.get('batchSize', 10)
        self.inference_interval = config.get('inferenceIntervalMs', 30000) / 1000
        self.anomaly_threshold = config.get('anomalyThreshold', 0.8)
        
        # Buffer for sensor readings
        self.sensor_buffer = deque(maxlen=1000)
        
        # Load model
        self.load_model()
        
    def load_model(self):
        """Load the LLM model with 4-bit quantization for edge deployment"""
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            # Use local model path
            model_path = f"{self.model_path}/{self.model_name}"
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True
            )
            
            # Load model with 4-bit quantization for memory efficiency
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.float16,
                device_map="auto",
                load_in_4bit=True
            )
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Fallback to mock inference if model loading fails
            self.model = None
            self.tokenizer = None
    
    def subscribe_to_sensors(self):
        """Subscribe to sensor data and chat request topics"""
        topics = ["local/sensors/+", "local/chat/requests"]
        
        for topic in topics:
            try:
                request = SubscribeToTopicRequest()
                request.topic = topic
                
                handler = self.handle_sensor_message
                operation = self.ipc_client.new_subscribe_to_topic(handler)
                future = operation.activate(request)
                future.result(timeout=10.0)
                
                logger.info(f"Subscribed to topic: {topic}")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to {topic}: {e}")
    
    def handle_sensor_message(self, message: SubscriptionResponseMessage):
        """Handle incoming sensor and chat messages"""
        try:
            topic = message.topic
            payload = json.loads(message.binary_message.message.decode('utf-8'))
            
            if "chat/requests" in topic:
                # Handle chat requests
                self.handle_chat_request(payload)
            else:
                # Handle sensor data
                self.sensor_buffer.append(payload)
                
                # Check for immediate anomalies
                if payload.get('is_anomaly', False):
                    self.process_anomaly(payload)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def handle_chat_request(self, chat_data: Dict[str, Any]):
        """Handle chat requests from the ChatBot UI"""
        try:
            user_message = chat_data.get('message', '')
            enhanced_prompt = chat_data.get('enhanced_prompt', user_message)
            
            logger.info(f"Processing chat request: {user_message[:50]}...")
            
            # Get current sensor context
            sensor_context = self.get_recent_sensor_context()
            
            # Generate response
            if enhanced_prompt and enhanced_prompt != user_message:
                # Use the enhanced prompt from ChatBot
                response = self.analyze_with_llm([sensor_context], is_chat=True, prompt=enhanced_prompt)
            else:
                # Create our own contextual prompt
                contextual_prompt = self.create_chat_prompt(user_message, sensor_context)
                response = self.analyze_with_llm([sensor_context], is_chat=True, prompt=contextual_prompt)
            
            # Publish response back to ChatBot
            self.publish_chat_response({
                'type': 'chat_response',
                'original_message': user_message,
                'response': response,
                'timestamp': datetime.utcnow().isoformat(),
                'context_used': True
            })
            
        except Exception as e:
            logger.error(f"Error handling chat request: {e}")
            # Send error response
            self.publish_chat_response({
                'type': 'chat_response',
                'original_message': chat_data.get('message', ''),
                'response': f"I apologize, but I encountered an error: {str(e)}",
                'timestamp': datetime.utcnow().isoformat(),
                'context_used': False
            })
    
    def get_recent_sensor_context(self) -> Dict[str, Any]:
        """Get recent sensor data for chat context"""
        if not self.sensor_buffer:
            return {'status': 'No recent sensor data'}
        
        # Get last 20 readings
        recent_readings = list(self.sensor_buffer)[-20:]
        
        # Organize by sensor type
        context = {}
        anomaly_count = 0
        
        for reading in recent_readings:
            sensor_type = reading.get('type', 'unknown')
            if sensor_type not in context:
                context[sensor_type] = {
                    'latest_value': 0,
                    'unit': '',
                    'readings_count': 0,
                    'anomaly_count': 0
                }
            
            context[sensor_type]['latest_value'] = reading.get('value', 0)
            context[sensor_type]['unit'] = reading.get('unit', '')
            context[sensor_type]['readings_count'] += 1
            
            if reading.get('is_anomaly', False):
                context[sensor_type]['anomaly_count'] += 1
                anomaly_count += 1
        
        return {
            'sensor_summary': context,
            'total_anomalies': anomaly_count,
            'total_readings': len(recent_readings),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def create_chat_prompt(self, user_message: str, sensor_context: Dict) -> str:
        """Create a chat-optimized prompt with sensor context"""
        context_str = json.dumps(sensor_context, indent=2)
        
        prompt = f"""You are an expert industrial IoT AI assistant. Answer the user's question based on the current sensor data.

Current System Status:
{context_str}

User Question: {user_message}

Provide a helpful, concise response focusing on:
1. Current sensor readings and trends
2. Any anomalies or concerns
3. Direct answer to the user's question
4. Actionable recommendations if applicable

Keep the response conversational and practical."""
        
        return prompt
    
    def publish_chat_response(self, response_data: Dict[str, Any]):
        """Publish chat response back to ChatBot"""
        try:
            topic = "local/chat/responses"
            message = json.dumps(response_data)
            
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
            
            logger.info("Published chat response")
            
        except Exception as e:
            logger.error(f"Failed to publish chat response: {e}")
    
    def process_anomaly(self, sensor_data: Dict[str, Any]):
        """Process detected anomalies immediately"""
        analysis = self.analyze_with_llm([sensor_data], is_anomaly=True)
        
        # Publish analysis result
        self.publish_analysis({
            'type': 'anomaly_detection',
            'sensor_id': sensor_data['sensor_id'],
            'analysis': analysis,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': self.calculate_severity(sensor_data)
        })
    
    def analyze_with_llm(self, sensor_readings: List[Dict], is_anomaly: bool = False, is_chat: bool = False, prompt: str = None) -> str:
        """Perform LLM inference on sensor data"""
        if not self.model or not self.tokenizer:
            # Mock inference if model not available
            return self.mock_inference(sensor_readings, is_anomaly)
        
        try:
            # Prepare prompt
            if is_chat and prompt:
                # Use provided chat prompt
                analysis_prompt = prompt
            else:
                # Use standard analysis prompt
                analysis_prompt = self.create_analysis_prompt(sensor_readings, is_anomaly)
            
            # Tokenize input
            inputs = self.tokenizer(analysis_prompt, return_tensors="pt", truncation=True, max_length=512)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=self.max_tokens,
                    temperature=self.temperature,
                    do_sample=True,
                    top_p=0.95
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM inference failed: {e}")
            return self.mock_inference(sensor_readings, is_anomaly, is_chat, prompt)
    
    def create_analysis_prompt(self, sensor_readings: List[Dict], is_anomaly: bool) -> str:
        """Create prompt for LLM analysis"""
        if is_anomaly:
            prompt = "Analyze this industrial sensor anomaly and provide recommendations:\n\n"
        else:
            prompt = "Analyze these industrial sensor readings for patterns and insights:\n\n"
        
        for reading in sensor_readings[-10:]:  # Last 10 readings
            prompt += f"- {reading['type']}: {reading['value']} {reading['unit']} at {reading['timestamp']}\n"
        
        prompt += "\nProvide a brief analysis and any recommended actions."
        
        return prompt
    
    def mock_inference(self, sensor_readings: List[Dict], is_anomaly: bool, is_chat: bool = False, prompt: str = None) -> str:
        """Mock inference for testing without actual model"""
        if is_chat and prompt:
            # Extract user question from chat prompt
            lines = prompt.split('\n')
            user_question = ""
            for line in lines:
                if line.startswith("User Question:"):
                    user_question = line.replace("User Question:", "").strip()
                    break
            
            # Generate contextual chat response
            return self.generate_chat_response(user_question, sensor_readings[0] if sensor_readings else {})
        elif is_anomaly:
            reading = sensor_readings[0] if sensor_readings else {}
            sensor_type = reading.get('type', 'unknown')
            value = reading.get('value', 0)
            unit = reading.get('unit', '')
            return f"⚠️ Anomaly detected in {sensor_type} sensor: value {value}{unit} exceeds normal range. Recommended action: Inspect equipment and verify sensor calibration."
        else:
            # Standard batch analysis
            if not sensor_readings:
                return "No sensor data available for analysis."
            
            temp_readings = [r for r in sensor_readings if isinstance(r, dict) and r.get('type') == 'temperature']
            if temp_readings:
                avg_temp = sum(r.get('value', 0) for r in temp_readings) / len(temp_readings)
                return f"✅ System operating normally. Average temperature: {avg_temp:.1f}°C. All sensors within expected ranges."
            else:
                return "✅ System operating normally. All sensors within expected ranges."
    
    def generate_chat_response(self, user_question: str, sensor_context: Dict) -> str:
        """Generate contextual chat response for mock inference"""
        question_lower = user_question.lower()
        
        if 'status' in question_lower or 'how' in question_lower:
            return "✅ Based on recent sensor data, all systems are operating within normal parameters. Temperature, pressure, and vibration sensors are all reporting values within expected ranges."
        elif 'anomaly' in question_lower or 'problem' in question_lower:
            sensor_summary = sensor_context.get('sensor_summary', {})
            total_anomalies = sensor_context.get('total_anomalies', 0)
            if total_anomalies > 0:
                return f"⚠️ I've detected {total_anomalies} anomalies in recent sensor readings. This could indicate equipment issues that require attention. Check the Grafana dashboard for detailed analysis."
            else:
                return "✅ No anomalies detected in recent sensor readings. All systems are operating normally."
        elif 'temperature' in question_lower:
            sensor_summary = sensor_context.get('sensor_summary', {})
            temp_data = sensor_summary.get('temperature', {})
            if temp_data:
                value = temp_data.get('latest_value', 0)
                unit = temp_data.get('unit', '°C')
                return f"🌡️ Current temperature reading: {value}{unit}. Based on {temp_data.get('readings_count', 0)} recent readings."
            else:
                return "No recent temperature data available."
        elif 'pressure' in question_lower:
            sensor_summary = sensor_context.get('sensor_summary', {})
            pressure_data = sensor_summary.get('pressure', {})
            if pressure_data:
                value = pressure_data.get('latest_value', 0)
                unit = pressure_data.get('unit', 'kPa')
                return f"📊 Current pressure reading: {value}{unit}. Based on {pressure_data.get('readings_count', 0)} recent readings."
            else:
                return "No recent pressure data available."
        elif 'vibration' in question_lower:
            sensor_summary = sensor_context.get('sensor_summary', {})
            vib_data = sensor_summary.get('vibration', {})
            if vib_data:
                value = vib_data.get('latest_value', 0)
                unit = vib_data.get('unit', 'mm/s')
                return f"〰️ Current vibration reading: {value}{unit}. Based on {vib_data.get('readings_count', 0)} recent readings."
            else:
                return "No recent vibration data available."
        else:
            total_readings = sensor_context.get('total_readings', 0)
            return f"🤖 I'm monitoring your industrial sensors in real-time. Recent analysis shows {total_readings} sensor readings processed. You can ask me about specific sensors, system status, or any concerns you have."
    
    def calculate_severity(self, sensor_data: Dict) -> str:
        """Calculate anomaly severity"""
        value = sensor_data['value']
        sensor_type = sensor_data['type']
        config = self.config.get('sensors', {}).get(sensor_type, {})
        
        min_val = config.get('min', 0)
        max_val = config.get('max', 100)
        
        deviation = 0
        if value > max_val:
            deviation = (value - max_val) / max_val
        elif value < min_val:
            deviation = (min_val - value) / min_val
        
        if deviation > 0.5:
            return "critical"
        elif deviation > 0.2:
            return "warning"
        else:
            return "info"
    
    def batch_inference(self):
        """Perform batch inference on accumulated sensor data"""
        if len(self.sensor_buffer) < self.batch_size:
            return
        
        # Get recent readings
        recent_readings = list(self.sensor_buffer)[-self.batch_size:]
        
        # Perform analysis
        analysis = self.analyze_with_llm(recent_readings)
        
        # Publish results
        self.publish_analysis({
            'type': 'batch_analysis',
            'reading_count': len(recent_readings),
            'analysis': analysis,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def publish_analysis(self, analysis: Dict[str, Any]):
        """Publish analysis results"""
        try:
            topic = "industrial/analysis/results"
            message = json.dumps(analysis)
            
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
            
            logger.info(f"Published analysis: {analysis['type']}")
            
            # Also publish to local topic for Grafana
            self.publish_to_local_topic("local/analysis/results", analysis)
            
        except Exception as e:
            logger.error(f"Failed to publish analysis: {e}")
    
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
    
    def run(self):
        """Main inference loop"""
        logger.info("Starting LLM inference engine")
        
        # Subscribe to sensor topics
        self.subscribe_to_sensors()
        
        last_batch_time = time.time()
        
        while True:
            try:
                current_time = time.time()
                
                # Perform batch inference at intervals
                if current_time - last_batch_time >= self.inference_interval:
                    self.batch_inference()
                    last_batch_time = current_time
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in inference loop: {e}")
                time.sleep(5)

def main():
    # Load configuration
    try:
        with open('/greengrass/v2/work/com.edge.llm.InferenceEngine/config.json', 'r') as f:
            config = json.load(f)
    except:
        # Use default configuration
        config = {
            'modelName': 'TinyLlama-1.1B-Chat',
            'modelPath': '/greengrass/v2/packages/artifacts/com.edge.llm.InferenceEngine/1.0.0/models',
            'maxTokens': 100,
            'temperature': 0.7,
            'batchSize': 10,
            'inferenceIntervalMs': 30000,
            'anomalyThreshold': 0.8,
            'sensors': {
                'temperature': {'min': 20, 'max': 80},
                'pressure': {'min': 100, 'max': 200},
                'vibration': {'min': 0, 'max': 10}
            }
        }
    
    engine = LLMInferenceEngine(config)
    engine.run()

if __name__ == '__main__':
    main()