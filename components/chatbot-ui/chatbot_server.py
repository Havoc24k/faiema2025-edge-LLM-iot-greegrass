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
            return {"history": list(self.chat_history)}\n        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.connect_websocket(websocket)
    
    async def connect_websocket(self, websocket: WebSocket):
        \"\"\"Handle WebSocket connections for real-time updates\"\"\"\n        await websocket.accept()\n        self.active_connections.append(websocket)\n        \n        try:\n            while True:\n                # Keep connection alive and listen for messages\n                data = await websocket.receive_text()\n                message_data = json.loads(data)\n                \n                if message_data.get('type') == 'chat':\n                    # Process chat message\n                    response = await self.query_llm(message_data.get('message', ''))\n                    await websocket.send_text(json.dumps({\n                        'type': 'response',\n                        'message': response,\n                        'timestamp': datetime.utcnow().isoformat()\n                    }))\n                    \n        except Exception as e:\n            logger.error(f\"WebSocket error: {e}\")\n        finally:\n            if websocket in self.active_connections:\n                self.active_connections.remove(websocket)
    
    async def broadcast_message(self, message: Dict):
        \"\"\"Broadcast message to all connected WebSocket clients\"\"\"\n        if self.active_connections:\n            message_json = json.dumps(message)\n            # Create a copy of connections to avoid modification during iteration\n            connections_copy = self.active_connections.copy()\n            for connection in connections_copy:\n                try:\n                    await connection.send_text(message_json)\n                except:\n                    # Remove broken connections\n                    if connection in self.active_connections:\n                        self.active_connections.remove(connection)
    
    async def query_llm(self, user_message: str) -> str:
        \"\"\"Send query to LLM inference engine and get response\"\"\"\n        try:\n            # Get sensor context\n            sensor_context = await self.get_sensor_context_for_llm()\n            \n            # Create enhanced prompt with sensor data context\n            enhanced_prompt = self.create_context_aware_prompt(user_message, sensor_context)\n            \n            # Publish to LLM inference engine topic\n            chat_request = {\n                \"type\": \"chat_query\",\n                \"message\": user_message,\n                \"enhanced_prompt\": enhanced_prompt,\n                \"timestamp\": datetime.utcnow().isoformat(),\n                \"context\": \"chatbot\"\n            }\n            \n            # Send request to LLM\n            await self.publish_to_llm(chat_request)\n            \n            # Wait for response (in production, this would be handled via subscription)\n            # For now, return a contextual response\n            return self.generate_contextual_response(user_message, sensor_context)\n            \n        except Exception as e:\n            logger.error(f\"Error querying LLM: {e}\")\n            return f\"I apologize, but I encountered an error processing your request: {str(e)}\"
    
    def create_context_aware_prompt(self, user_message: str, sensor_context: Dict) -> str:
        \"\"\"Create an enhanced prompt with sensor data context\"\"\"\n        context_prompt = f\"\"\"You are an industrial IoT AI assistant with access to real-time sensor data. 
        
Current sensor status:
{json.dumps(sensor_context, indent=2)}

User question: {user_message}

Please provide a helpful response based on the current sensor data. Focus on:
- Current system status and health
- Any anomalies or patterns in the data
- Actionable insights or recommendations
- Answer the user's specific question in context

Keep responses concise and practical.\"\"\"\n        \n        return context_prompt
    
    async def get_sensor_context_for_llm(self) -> Dict:
        \"\"\"Get recent sensor data for LLM context\"\"\"\n        # Get recent sensor data (last 30 minutes)\n        cutoff_time = datetime.utcnow() - timedelta(minutes=30)\n        recent_data = []\n        \n        for data in self.sensor_data:\n            try:\n                data_time = datetime.fromisoformat(data.get('timestamp', ''))\n                if data_time >= cutoff_time:\n                    recent_data.append(data)\n            except:\n                continue\n        \n        if not recent_data:\n            return {\"status\": \"No recent sensor data available\"}\n        \n        # Summarize recent data\n        summary = {}\n        total_anomalies = 0\n        \n        for data in recent_data:\n            sensor_type = data.get('type', 'unknown')\n            if sensor_type not in summary:\n                summary[sensor_type] = []\n            \n            summary[sensor_type].append({\n                \"value\": data.get('value'),\n                \"unit\": data.get('unit'),\n                \"is_anomaly\": data.get('is_anomaly', False),\n                \"timestamp\": data.get('timestamp')\n            })\n            \n            if data.get('is_anomaly', False):\n                total_anomalies += 1\n        \n        # Get latest analysis results\n        latest_analysis = list(self.analysis_results)[-5:] if self.analysis_results else []\n        \n        return {\n            \"sensor_data_summary\": summary,\n            \"total_anomalies_30min\": total_anomalies,\n            \"total_readings_30min\": len(recent_data),\n            \"latest_llm_analysis\": latest_analysis\n        }
    
    def generate_contextual_response(self, user_message: str, sensor_context: Dict) -> str:
        \"\"\"Generate a contextual response based on sensor data (fallback for when LLM is not available)\"\"\"\n        message_lower = user_message.lower()\n        \n        # Analyze user intent\n        if any(word in message_lower for word in ['status', 'how', 'current', 'now']):\n            return self.get_system_status_response(sensor_context)\n        elif any(word in message_lower for word in ['anomaly', 'alert', 'problem', 'issue']):\n            return self.get_anomaly_response(sensor_context)\n        elif any(word in message_lower for word in ['temperature', 'temp', 'hot', 'cold']):\n            return self.get_temperature_response(sensor_context)\n        elif any(word in message_lower for word in ['pressure']):\n            return self.get_pressure_response(sensor_context)\n        elif any(word in message_lower for word in ['vibration', 'vibrate']):\n            return self.get_vibration_response(sensor_context)\n        else:\n            return self.get_general_response(sensor_context)
    
    def get_system_status_response(self, context: Dict) -> str:\n        \"\"\"Generate system status response\"\"\"\n        if context.get(\"status\") == \"No recent sensor data available\":\n            return \"I don't have recent sensor data to provide a system status. Please check if the sensors are connected and transmitting data.\"\n        \n        anomalies = context.get(\"total_anomalies_30min\", 0)\n        readings = context.get(\"total_readings_30min\", 0)\n        \n        if anomalies == 0:\n            return f\"✅ System Status: All sensors are operating normally. I've analyzed {readings} readings in the last 30 minutes with no anomalies detected.\"\n        else:\n            return f\"⚠️ System Status: {anomalies} anomalies detected out of {readings} readings in the last 30 minutes. Please check the Grafana dashboard for detailed analysis.\"\n    \n    def get_anomaly_response(self, context: Dict) -> str:\n        \"\"\"Generate anomaly-focused response\"\"\"\n        anomalies = context.get(\"total_anomalies_30min\", 0)\n        \n        if anomalies == 0:\n            return \"No anomalies detected in the last 30 minutes. All sensor readings are within expected ranges.\"\n        else:\n            return f\"I've detected {anomalies} anomalies in the last 30 minutes. These could indicate equipment issues or environmental changes that require attention.\"\n    \n    def get_temperature_response(self, context: Dict) -> str:\n        \"\"\"Generate temperature-specific response\"\"\"\n        sensor_data = context.get(\"sensor_data_summary\", {})\n        temp_data = sensor_data.get(\"temperature\", [])\n        \n        if not temp_data:\n            return \"No recent temperature data available.\"\n        \n        latest_temp = temp_data[-1] if temp_data else None\n        if latest_temp:\n            value = latest_temp.get(\"value\", 0)\n            unit = latest_temp.get(\"unit\", \"°C\")\n            is_anomaly = latest_temp.get(\"is_anomaly\", False)\n            \n            status = \"⚠️ ANOMALY\" if is_anomaly else \"✅ Normal\"\n            return f\"Latest temperature reading: {value}{unit} - {status}. Based on {len(temp_data)} readings in the last 30 minutes.\"\n        \n        return \"Unable to retrieve specific temperature information.\"\n    \n    def get_pressure_response(self, context: Dict) -> str:\n        \"\"\"Generate pressure-specific response\"\"\"\n        sensor_data = context.get(\"sensor_data_summary\", {})\n        pressure_data = sensor_data.get(\"pressure\", [])\n        \n        if not pressure_data:\n            return \"No recent pressure data available.\"\n        \n        latest_pressure = pressure_data[-1] if pressure_data else None\n        if latest_pressure:\n            value = latest_pressure.get(\"value\", 0)\n            unit = latest_pressure.get(\"unit\", \"kPa\")\n            is_anomaly = latest_pressure.get(\"is_anomaly\", False)\n            \n            status = \"⚠️ ANOMALY\" if is_anomaly else \"✅ Normal\"\n            return f\"Latest pressure reading: {value}{unit} - {status}. Based on {len(pressure_data)} readings in the last 30 minutes.\"\n        \n        return \"Unable to retrieve specific pressure information.\"\n    \n    def get_vibration_response(self, context: Dict) -> str:\n        \"\"\"Generate vibration-specific response\"\"\"\n        sensor_data = context.get(\"sensor_data_summary\", {})\n        vib_data = sensor_data.get(\"vibration\", [])\n        \n        if not vib_data:\n            return \"No recent vibration data available.\"\n        \n        latest_vib = vib_data[-1] if vib_data else None\n        if latest_vib:\n            value = latest_vib.get(\"value\", 0)\n            unit = latest_vib.get(\"unit\", \"mm/s\")\n            is_anomaly = latest_vib.get(\"is_anomaly\", False)\n            \n            status = \"⚠️ ANOMALY\" if is_anomaly else \"✅ Normal\"\n            return f\"Latest vibration reading: {value}{unit} - {status}. Based on {len(vib_data)} readings in the last 30 minutes.\"\n        \n        return \"Unable to retrieve specific vibration information.\"\n    \n    def get_general_response(self, context: Dict) -> str:\n        \"\"\"Generate general response\"\"\"\n        readings = context.get(\"total_readings_30min\", 0)\n        anomalies = context.get(\"total_anomalies_30min\", 0)\n        \n        return f\"I'm monitoring your industrial sensors in real-time. In the last 30 minutes, I've processed {readings} sensor readings with {anomalies} anomalies detected. You can ask me about specific sensors, system status, or any anomalies you're concerned about.\"\n    \n    async def publish_to_llm(self, message: Dict):\n        \"\"\"Publish message to LLM inference engine\"\"\"\n        try:\n            topic = \"local/chat/requests\"\n            message_json = json.dumps(message)\n            \n            request = PublishToTopicRequest()\n            request.topic = topic\n            publish_message = PublishMessage()\n            publish_message.binary_message = BinaryMessage()\n            publish_message.binary_message.message = message_json.encode('utf-8')\n            request.publish_message = publish_message\n            \n            operation = self.ipc_client.new_publish_to_topic()\n            operation.activate(request)\n            future = operation.get_response()\n            future.result(timeout=5.0)\n            \n            logger.info(f\"Published chat request to LLM\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to publish to LLM: {e}\")\n    \n    def subscribe_to_topics(self):\n        \"\"\"Subscribe to sensor data and analysis topics\"\"\"\n        topics = [\n            \"local/sensors/+\",\n            \"local/analysis/results\",\n            \"local/chat/responses\"\n        ]\n        \n        for topic in topics:\n            try:\n                request = SubscribeToTopicRequest()\n                request.topic = topic\n                \n                handler = self.handle_message\n                operation = self.ipc_client.new_subscribe_to_topic(handler)\n                future = operation.activate(request)\n                future.result(timeout=10.0)\n                \n                logger.info(f\"Subscribed to topic: {topic}\")\n                \n            except Exception as e:\n                logger.error(f\"Failed to subscribe to {topic}: {e}\")\n    \n    def handle_message(self, message: SubscriptionResponseMessage):\n        \"\"\"Handle incoming MQTT messages\"\"\"\n        try:\n            topic = message.topic\n            payload = json.loads(message.binary_message.message.decode('utf-8'))\n            \n            if \"sensors\" in topic:\n                # Store sensor data\n                self.sensor_data.append(payload)\n            elif \"analysis\" in topic:\n                # Store analysis results\n                self.analysis_results.append(payload)\n            elif \"chat/responses\" in topic:\n                # Handle LLM responses\n                asyncio.create_task(self.broadcast_message(payload))\n                \n        except Exception as e:\n            logger.error(f\"Error handling message: {e}\")\n    \n    async def start_server(self):\n        \"\"\"Start the ChatBot web server\"\"\"\n        logger.info(f\"Starting ChatBot UI server on port {self.web_port}\")\n        \n        # Subscribe to topics first\n        self.subscribe_to_topics()\n        \n        # Start the web server\n        config = uvicorn.Config(\n            self.app,\n            host=\"0.0.0.0\",\n            port=self.web_port,\n            log_level=\"info\" if self.debug_mode else \"warning\"\n        )\n        server = uvicorn.Server(config)\n        await server.serve()

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
        logger.info(\"ChatBot server stopped\")

if __name__ == '__main__':
    main()