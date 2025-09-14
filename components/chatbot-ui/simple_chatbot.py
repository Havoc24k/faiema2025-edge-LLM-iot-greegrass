#!/usr/bin/env python3

import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template_string
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EdgeLLMChatBot:
    def __init__(self):
        self.app = Flask(__name__)
        self.influxdb_url = "http://localhost:8086"
        self.influxdb_database = "sensors"

        logger.info("ChatBot connecting to InfluxDB at: %s", self.influxdb_url)
        logger.info("Loading TinyLlama-1.1B (optimized for edge inference)...")

        # Initialize TinyLlama - specifically designed for edge deployment
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            # Use GPU if available, fallback to CPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device: %s", device)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else "cpu"
            )
            # Add pad token if needed
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            logger.info("Successfully loaded TinyLlama model")
            self.model_loaded = True
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            self.tokenizer = None
            self.model = None
            self.model_loaded = False

        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edge LLM IoT ChatBot</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .chat-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .chat-history {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #fafafa;
            border-radius: 5px;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        .user-message {
            background-color: #007bff;
            color: white;
            text-align: right;
            margin-left: 20%;
        }
        .bot-message {
            background-color: #e9ecef;
            color: #333;
            margin-right: 20%;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        #sendButton {
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        #sendButton:hover {
            background-color: #0056b3;
        }
        #sendButton:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            text-align: center;
            color: #666;
            font-style: italic;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>🤖 Edge LLM IoT ChatBot</h1>
    <div class="status">Ask me about sensor data, system status, or any IoT-related questions!</div>

    <div class="chat-container">
        <div class="chat-history" id="chatHistory">
            <div class="message bot-message">
                <strong>ChatBot:</strong> Hello! I'm your Edge LLM IoT assistant. I can analyze sensor data and answer questions about your industrial systems. What would you like to know?
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Ask me about sensors, anomalies, temperature, etc..." onkeypress="handleKeyPress(event)">
            <button id="sendButton" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatHistory = document.getElementById('chatHistory');

            const message = input.value.trim();
            if (!message) return;

            // Disable input while processing
            sendButton.disabled = true;
            sendButton.textContent = 'Thinking...';

            // Add user message to chat
            addMessage(message, 'user');

            // Clear input
            input.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({message: message}),
                });

                const data = await response.json();

                if (response.ok) {
                    addMessage(data.response, 'bot');
                } else {
                    addMessage('Sorry, I encountered an error processing your request.', 'bot');
                }
            } catch (error) {
                console.error('Error:', error);
                addMessage('Sorry, I could not connect to the server.', 'bot');
            } finally {
                // Re-enable input
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                input.focus();
            }
        }

        function addMessage(message, type) {
            const chatHistory = document.getElementById('chatHistory');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;

            const sender = type === 'user' ? 'You' : 'ChatBot';
            messageDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;

            chatHistory.appendChild(messageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        // Focus on input when page loads
        window.onload = function() {
            document.getElementById('messageInput').focus();
        }
    </script>
</body>
</html>
            """)

        @self.app.route('/chat', methods=['POST'])
        def chat():
            try:
                data = request.get_json()
                user_message = data.get('message', '').strip()

                if not user_message:
                    return jsonify({'error': 'Message cannot be empty'}), 400

                logger.info("Received chat message: %s", user_message)
                response = self.analyze_query(user_message)

                return jsonify({'response': response})

            except Exception as e:
                logger.error("Error processing chat request: %s", e)
                return jsonify({'error': 'Internal server error'}), 500

    def get_sensor_data(self) -> Dict[str, Any]:
        """Get sensor data directly from InfluxDB"""
        try:
            # Query to get recent sensor data from InfluxDB
            query = 'SELECT * FROM "sensor_data" ORDER BY time DESC LIMIT 100'
            params = {
                'db': self.influxdb_database,
                'q': query
            }

            response = requests.get(f"{self.influxdb_url}/query", params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully retrieved sensor data from InfluxDB")
                return self.parse_influxdb_response(data)
            else:
                logger.error("InfluxDB query failed: %s", response.status_code)
                return {"error": "Failed to retrieve sensor data"}

        except Exception as e:
            logger.error("Error querying InfluxDB: %s", e)
            return {"error": str(e)}

    def parse_influxdb_response(self, influx_data: Dict) -> Dict[str, Any]:
        """Parse InfluxDB response into sensor data format"""
        try:
            if not influx_data.get('results') or not influx_data['results'][0].get('series'):
                return {"sensors": {}, "message": "No sensor data available"}

            series = influx_data['results'][0]['series'][0]
            columns = series['columns']
            values = series['values']

            sensors = {}
            for row in values:
                # Create a dict from columns and values
                sensor_entry = dict(zip(columns, row))

                sensor_id = sensor_entry.get('sensor_id', 'unknown')
                sensors[sensor_id] = {
                    'type': sensor_entry.get('sensor_type', 'unknown'),
                    'value': sensor_entry.get('value', 0),
                    'unit': sensor_entry.get('unit', ''),
                    'is_anomaly': sensor_entry.get('is_anomaly', False),
                    'timestamp': sensor_entry.get('time', '')
                }

            return {"sensors": sensors}

        except Exception as e:
            logger.error("Error parsing InfluxDB response: %s", e)
            return {"sensors": {}, "error": str(e)}

    def analyze_query(self, query: str) -> str:
        """Process user query with LLM using sensor data"""
        sensor_data = self.get_sensor_data()

        if self.model_loaded:
            return self.generate_llm_response(query, sensor_data)
        else:
            return "Sorry, the AI model is not available. Please try again later."

    def generate_llm_response(self, query: str, sensor_data: Dict[str, Any]) -> str:
        """Generate response using TinyLlama with sensor data context"""
        try:
            # Create sensor context summary
            sensors_summary = self.create_sensor_summary(sensor_data)
            logger.info("Sensor summary for LLM: %s", sensors_summary)

            # Create more explicit prompt for TinyLlama
            context_prompt = f"""You are monitoring an industrial IoT system.

CURRENT SENSOR STATUS: {sensors_summary}

Based on this real sensor data, answer the user's question about the system."""

            # TinyLlama chat format with clear role definition
            chat_prompt = f"<|system|>\n{context_prompt}</s>\n<|user|>\n{query}</s>\n<|assistant|>\n"

            # Tokenize and move to device
            inputs = self.tokenizer(chat_prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    max_new_tokens=80,
                    temperature=0.3,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            # Decode response
            response = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)

            # Clean up response
            response = response.strip()
            if not response or len(response) < 5:
                return "I'm analyzing the sensor data. Could you rephrase your question?"

            logger.info("LLM generated response: %s", response[:100] + "..." if len(response) > 100 else response)
            return response

        except Exception as e:
            logger.error("LLM generation error: %s", e)
            return "Sorry, I'm having trouble processing your request right now. Please try again."

    def create_sensor_summary(self, sensor_data: Dict[str, Any]) -> str:
        """Create a brief sensor summary for LLM context"""
        if not sensor_data.get('sensors'):
            return "No sensor data available"

        sensors = sensor_data['sensors']
        sensor_types = {}
        anomaly_count = 0

        for sensor_id, data in sensors.items():
            sensor_type = data.get('type', 'unknown')
            sensor_types[sensor_type] = sensor_types.get(sensor_type, 0) + 1
            if data.get('is_anomaly', False):
                anomaly_count += 1

        type_summary = ", ".join([f"{count} {stype}" for stype, count in sensor_types.items()])
        status = f"Monitoring {len(sensors)} sensors ({type_summary})"
        if anomaly_count > 0:
            status += f" with {anomaly_count} anomalies detected"
        else:
            status += " - all normal"

        return status


    def run(self, host='0.0.0.0', port=8080):
        logger.info("Starting Edge LLM IoT ChatBot on port %d", port)
        self.app.run(host=host, port=port, debug=False)

def main():
    chatbot = EdgeLLMChatBot()
    chatbot.run()

if __name__ == '__main__':
    main()