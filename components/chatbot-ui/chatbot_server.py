#!/usr/bin/env python3

import json
import logging
import asyncio
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional
from pathlib import Path
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
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

class ChatMessage(BaseModel):
    message: str
    timestamp: Optional[str] = None

class ChatBotServer:
    def __init__(self, config: Dict):
        self.config = config
        self.web_port = config.get('webPort', 8080)
        self.chat_history_limit = config.get('chatHistoryLimit', 50)
        self.retention_hours = config.get('sensorDataRetentionHours', 24)
        self.debug_mode = config.get('enableDebugMode', True)
        
        # Data storage
        self.sensor_data = deque(maxlen=1000)  # Store recent sensor readings
        self.analysis_results = deque(maxlen=100)  # Store LLM analysis results
        self.chat_history = deque(maxlen=self.chat_history_limit)
        
        # IPC Client for Greengrass communication
        self.ipc_client = awsiot.greengrasscoreipc.connect()
        
        # FastAPI setup
        self.app = FastAPI(title="Edge LLM ChatBot", version="1.0.0")
        self.setup_routes()
        self.setup_static_files()
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
    def setup_static_files(self):
        """Setup static files and templates"""
        component_path = Path(__file__).parent
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(component_path / "static")), name="static")
        
        # Setup templates
        self.templates = Jinja2Templates(directory=str(component_path / "templates"))
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def chat_interface(request: Request):
            return self.templates.TemplateResponse("index.html", {"request": request})
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        @self.app.get("/sensor-summary")
        async def get_sensor_summary():
            """Get recent sensor data summary for context"""
            if not self.sensor_data:
                return {"message": "No recent sensor data available"}
            
            # Get data from last hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            recent_data = []
            
            for data in self.sensor_data:
                try:
                    data_time = datetime.fromisoformat(data.get('timestamp', ''))
                    if data_time >= cutoff_time:
                        recent_data.append(data)
                except:
                    continue
            
            if not recent_data:
                return {"message": "No recent sensor data in the last hour"}
            
            # Summarize by sensor type
            summary = {}
            anomaly_count = 0
            
            for data in recent_data:
                sensor_type = data.get('type', 'unknown')
                if sensor_type not in summary:
                    summary[sensor_type] = {
                        'count': 0,
                        'avg_value': 0,
                        'min_value': float('inf'),
                        'max_value': float('-inf'),
                        'unit': data.get('unit', '')
                    }
                
                value = data.get('value', 0)
                summary[sensor_type]['count'] += 1
                summary[sensor_type]['avg_value'] += value
                summary[sensor_type]['min_value'] = min(summary[sensor_type]['min_value'], value)
                summary[sensor_type]['max_value'] = max(summary[sensor_type]['max_value'], value)
                
                if data.get('is_anomaly', False):
                    anomaly_count += 1
            
            # Calculate averages
            for sensor_type in summary:
                if summary[sensor_type]['count'] > 0:
                    summary[sensor_type]['avg_value'] /= summary[sensor_type]['count']
                    summary[sensor_type]['avg_value'] = round(summary[sensor_type]['avg_value'], 2)
            
            return {
                "sensor_summary": summary,
                "anomaly_count": anomaly_count,
                "total_readings": len(recent_data),
                "time_range": "last 1 hour"
            }
        
        @self.app.post("/chat")
        async def chat_with_llm(message: ChatMessage):
            """Send message to LLM and get response"""
            user_message = message.message.strip()
            if not user_message:
                raise HTTPException(status_code=400, detail="Message cannot be empty")
            
            # Add user message to history
            chat_entry = {
                "type": "user",
                "message": user_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.chat_history.append(chat_entry)
            
            # Send to LLM for processing
            llm_response = await self.query_llm(user_message)
            
            # Add LLM response to history
            response_entry = {
                "type": "assistant",
                "message": llm_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.chat_history.append(response_entry)
            
            # Broadcast to all connected WebSocket clients
            await self.broadcast_message(response_entry)
            
            return response_entry
        
        @self.app.get("/chat-history")
        async def get_chat_history():
            """Get recent chat history"""
            return {"history": list(self.chat_history)}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.connect_websocket(websocket)
    
    async def connect_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections for real-time updates"""
        await websocket.accept()
        self.active_connections.append(websocket)

        try:
            while True:
                # Keep connection alive and listen for messages
                data = await websocket.receive_text()
                message_data = json.loads(data)

                if message_data.get('type') == 'chat':
                    # Process chat message
                    response = await self.query_llm(message_data.get('message', ''))
                    await websocket.send_text(json.dumps({
                        'type': 'response',
                        'message': response,
                        'timestamp': datetime.utcnow().isoformat()
                    }))

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast_message(self, message: Dict):
        """Broadcast message to all connected WebSocket clients"""
        if self.active_connections:
            message_json = json.dumps(message)
            # Create a copy of connections to avoid modification during iteration
            connections_copy = self.active_connections.copy()
            for connection in connections_copy:
                try:
                    await connection.send_text(message_json)
                except:
                    # Remove broken connections
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
    
    async def query_llm(self, user_message: str) -> str:
        """Send query to LLM inference engine and get response"""
        try:
            # Get sensor context
            sensor_context = await self.get_sensor_context_for_llm()

            # Create enhanced prompt with sensor data context
            enhanced_prompt = self.create_context_aware_prompt(user_message, sensor_context)

            # Publish to LLM inference engine topic
            chat_request = {
                "type": "chat_query",
                "message": user_message,
                "enhanced_prompt": enhanced_prompt,
                "timestamp": datetime.utcnow().isoformat(),
                "context": "chatbot"
            }

            # Send request to LLM
            await self.publish_to_llm(chat_request)

            # Wait for response (in production, this would be handled via subscription)
            # For now, return a contextual response
            return self.generate_contextual_response(user_message, sensor_context)

        except Exception as e:
            logger.error(f"Error querying LLM: {e}")
            return f"I apologize, but I encountered an error processing your request: {str(e)}"
    
    def create_context_aware_prompt(self, user_message: str, sensor_context: Dict) -> str:
        """Create an enhanced prompt with sensor data context"""
        context_prompt = f"""You are an industrial IoT AI assistant with access to real-time sensor data.

Current sensor status:
{json.dumps(sensor_context, indent=2)}

User question: {user_message}

Please provide a helpful response based on the current sensor data. Focus on:
- Current system status and health
- Any anomalies or patterns in the data
- Actionable insights or recommendations
- Answer the user's specific question in context

Keep responses concise and practical."""

        return context_prompt
    
    async def get_sensor_context_for_llm(self) -> Dict:
        """Get recent sensor data for LLM context"""
        # Get recent sensor data (last 30 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        recent_data = []

        for data in self.sensor_data:
            try:
                data_time = datetime.fromisoformat(data.get('timestamp', ''))
                if data_time >= cutoff_time:
                    recent_data.append(data)
            except:
                continue

        if not recent_data:
            return {"status": "No recent sensor data available"}

        # Summarize recent data
        summary = {}
        total_anomalies = 0

        for data in recent_data:
            sensor_type = data.get('type', 'unknown')
            if sensor_type not in summary:
                summary[sensor_type] = []

            summary[sensor_type].append({
                "value": data.get('value'),
                "unit": data.get('unit'),
                "is_anomaly": data.get('is_anomaly', False),
                "timestamp": data.get('timestamp')
            })

            if data.get('is_anomaly', False):
                total_anomalies += 1

        # Get latest analysis results
        latest_analysis = list(self.analysis_results)[-5:] if self.analysis_results else []

        return {
            "sensor_data_summary": summary,
            "total_anomalies_30min": total_anomalies,
            "total_readings_30min": len(recent_data),
            "latest_llm_analysis": latest_analysis
        }
    
    def generate_contextual_response(self, user_message: str, sensor_context: Dict) -> str:
        """Generate a contextual response based on sensor data (fallback for when LLM is not available)"""
        message_lower = user_message.lower()

        # Analyze user intent
        if any(word in message_lower for word in ['status', 'how', 'current', 'now']):
            return self.get_system_status_response(sensor_context)
        elif any(word in message_lower for word in ['anomaly', 'alert', 'problem', 'issue']):
            return self.get_anomaly_response(sensor_context)
        elif any(word in message_lower for word in ['temperature', 'temp', 'hot', 'cold']):
            return self.get_temperature_response(sensor_context)
        elif any(word in message_lower for word in ['pressure']):
            return self.get_pressure_response(sensor_context)
        elif any(word in message_lower for word in ['vibration', 'vibrate']):
            return self.get_vibration_response(sensor_context)
        else:
            return self.get_general_response(sensor_context)
    
    def get_system_status_response(self, context: Dict) -> str:
        """Generate system status response"""
        if context.get("status") == "No recent sensor data available":
            return "I don't have recent sensor data to provide a system status. Please check if the sensors are connected and transmitting data."

        anomalies = context.get("total_anomalies_30min", 0)
        readings = context.get("total_readings_30min", 0)

        if anomalies == 0:
            return f"✅ System Status: All sensors are operating normally. I've analyzed {readings} readings in the last 30 minutes with no anomalies detected."
        else:
            return f"⚠️ System Status: {anomalies} anomalies detected out of {readings} readings in the last 30 minutes. Please check the Grafana dashboard for detailed analysis."

    def get_anomaly_response(self, context: Dict) -> str:
        """Generate anomaly-focused response"""
        anomalies = context.get("total_anomalies_30min", 0)

        if anomalies == 0:
            return "No anomalies detected in the last 30 minutes. All sensor readings are within expected ranges."
        else:
            return f"I've detected {anomalies} anomalies in the last 30 minutes. These could indicate equipment issues or environmental changes that require attention."

    def get_temperature_response(self, context: Dict) -> str:
        """Generate temperature-specific response"""
        sensor_data = context.get("sensor_data_summary", {})
        temp_data = sensor_data.get("temperature", [])

        if not temp_data:
            return "No recent temperature data available."

        latest_temp = temp_data[-1] if temp_data else None
        if latest_temp:
            value = latest_temp.get("value", 0)
            unit = latest_temp.get("unit", "°C")
            is_anomaly = latest_temp.get("is_anomaly", False)

            status = "⚠️ ANOMALY" if is_anomaly else "✅ Normal"
            return f"Latest temperature reading: {value}{unit} - {status}. Based on {len(temp_data)} readings in the last 30 minutes."

        return "Unable to retrieve specific temperature information."

    def get_pressure_response(self, context: Dict) -> str:
        """Generate pressure-specific response"""
        sensor_data = context.get("sensor_data_summary", {})
        pressure_data = sensor_data.get("pressure", [])

        if not pressure_data:
            return "No recent pressure data available."

        latest_pressure = pressure_data[-1] if pressure_data else None
        if latest_pressure:
            value = latest_pressure.get("value", 0)
            unit = latest_pressure.get("unit", "kPa")
            is_anomaly = latest_pressure.get("is_anomaly", False)

            status = "⚠️ ANOMALY" if is_anomaly else "✅ Normal"
            return f"Latest pressure reading: {value}{unit} - {status}. Based on {len(pressure_data)} readings in the last 30 minutes."

        return "Unable to retrieve specific pressure information."

    def get_vibration_response(self, context: Dict) -> str:
        """Generate vibration-specific response"""
        sensor_data = context.get("sensor_data_summary", {})
        vib_data = sensor_data.get("vibration", [])

        if not vib_data:
            return "No recent vibration data available."

        latest_vib = vib_data[-1] if vib_data else None
        if latest_vib:
            value = latest_vib.get("value", 0)
            unit = latest_vib.get("unit", "mm/s")
            is_anomaly = latest_vib.get("is_anomaly", False)

            status = "⚠️ ANOMALY" if is_anomaly else "✅ Normal"
            return f"Latest vibration reading: {value}{unit} - {status}. Based on {len(vib_data)} readings in the last 30 minutes."

        return "Unable to retrieve specific vibration information."

    def get_general_response(self, context: Dict) -> str:
        """Generate general response"""
        readings = context.get("total_readings_30min", 0)
        anomalies = context.get("total_anomalies_30min", 0)

        return f"I'm monitoring your industrial sensors in real-time. In the last 30 minutes, I've processed {readings} sensor readings with {anomalies} anomalies detected. You can ask me about specific sensors, system status, or any anomalies you're concerned about."

    async def publish_to_llm(self, message: Dict):
        """Publish message to LLM inference engine"""
        try:
            topic = "local/chat/requests"
            message_json = json.dumps(message)

            request = PublishToTopicRequest()
            request.topic = topic
            publish_message = PublishMessage()
            publish_message.binary_message = BinaryMessage()
            publish_message.binary_message.message = message_json.encode('utf-8')
            request.publish_message = publish_message

            operation = self.ipc_client.new_publish_to_topic()
            operation.activate(request)
            future = operation.get_response()
            future.result(timeout=5.0)

            logger.info("Published chat request to LLM")

        except Exception as e:
            logger.error(f"Failed to publish to LLM: {e}")

    def subscribe_to_topics(self):
        """Subscribe to sensor data and analysis topics"""
        topics = [
            "local/sensors/+",
            "local/analysis/results",
            "local/chat/responses"
        ]

        for topic in topics:
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
        """Handle incoming MQTT messages"""
        try:
            topic = message.topic
            payload = json.loads(message.binary_message.message.decode('utf-8'))

            if "sensors" in topic:
                # Store sensor data
                self.sensor_data.append(payload)
            elif "analysis" in topic:
                # Store analysis results
                self.analysis_results.append(payload)
            elif "chat/responses" in topic:
                # Handle LLM responses
                asyncio.create_task(self.broadcast_message(payload))

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def start_server(self):
        """Start the ChatBot web server"""
        logger.info(f"Starting ChatBot UI server on port {self.web_port}")

        # Subscribe to topics first
        self.subscribe_to_topics()

        # Start the web server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.web_port,
            log_level="info" if self.debug_mode else "warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

def main():
    # Load configuration
    try:
        with open('/greengrass/v2/work/com.edge.llm.ChatBotUI/config.json', 'r') as f:
            config = json.load(f)
    except:
        # Use default configuration
        config = {
            'webPort': 8080,
            'chatHistoryLimit': 50,
            'enableDebugMode': True,
            'sensorDataRetentionHours': 24
        }
    
    # Create and start the server
    chatbot_server = ChatBotServer(config)
    
    try:
        asyncio.run(chatbot_server.start_server())
    except KeyboardInterrupt:
        logger.info("ChatBot server stopped")

if __name__ == '__main__':
    main()