#!/usr/bin/env python3

import json
import logging
import requests
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template_string
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EdgeLLMChatBot:
    def __init__(self):
        self.app = Flask(__name__)
        # InfluxDB 2.x configuration
        self.influxdb_url = "http://localhost:8086"
        self.influxdb_org = "edge-llm"
        self.influxdb_bucket = "sensors"
        self.influxdb_token = "edge-llm-token-12345"  # Default token from setup

        logger.info("ChatBot connecting to InfluxDB at: %s", self.influxdb_url)
        logger.info("InfluxDB config - Org: %s, Bucket: %s", self.influxdb_org, self.influxdb_bucket)
        logger.info("Loading CodeLlama-7B (optimized for structured data analysis)...")

        # Initialize CodeLlama - better for structured data understanding
        self.model_name = "codellama/CodeLlama-7b-Instruct-hf"
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
            logger.info("Successfully loaded CodeLlama model")
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

                logger.info("=== CHAT REQUEST START ===")
                logger.info("Received user message: %s", user_message)

                response = self.analyze_query(user_message)

                logger.info("Final response sent to user: %s", response)
                logger.info("=== CHAT REQUEST END ===")

                return jsonify({'response': response})

            except Exception as e:
                logger.error("Error processing chat request: %s", e)
                return jsonify({'error': 'Internal server error'}), 500

    def get_sensor_data(self) -> Dict[str, Any]:
        """Get sensor data from InfluxDB 1.8 using InfluxQL"""
        try:
            # Query InfluxDB 1.8 using InfluxQL
            params = {
                'db': 'sensors',
                'q': "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 50"
            }

            response = requests.get(f"{self.influxdb_url}/query", params=params, timeout=10)

            if response.status_code == 200:
                return self.parse_influxql_response(response.json())
            else:
                logger.error("InfluxDB query failed: %d - %s", response.status_code, response.text)
                return {"error": f"InfluxDB query failed: {response.status_code}"}

        except Exception as e:
            logger.error("Error querying InfluxDB: %s", e, exc_info=True)
            return {"error": str(e)}

    def parse_influxql_response(self, influxql_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse InfluxDB 1.8 InfluxQL JSON response into sensor data format"""
        try:
            # Check for errors
            if 'error' in influxql_json:
                return {"error": influxql_json['error']}

            results = influxql_json.get('results', [])
            if not results:
                return {"sensors": {}, "message": "No sensor data available"}

            result = results[0]
            if 'error' in result:
                return {"error": result['error']}

            series = result.get('series', [])
            if not series:
                return {"sensors": {}, "message": "No sensor data available"}

            sensors = {}

            # Parse sensor data efficiently
            for serie in series:
                columns = serie.get('columns', [])
                values = serie.get('values', [])

                for i, value_row in enumerate(values):
                    if len(value_row) == len(columns):
                        row_data = dict(zip(columns, value_row))
                        sensor_id = row_data.get('sensor_id', f'sensor_{i}')

                        sensors[sensor_id] = {
                            'id': sensor_id,
                            'type': row_data.get('sensor_type', 'unknown'),
                            'value': float(row_data.get('value', 0)),
                            'timestamp': row_data.get('time', ''),
                            'equipment_id': row_data.get('equipment_id', 'unknown'),
                            'location': row_data.get('location', 'unknown'),
                            'is_anomaly': bool(row_data.get('is_anomaly', False))
                        }
            return {
                "sensors": sensors,
                "message": f"Retrieved {len(sensors)} sensors"
            }

        except Exception as e:
            logger.error("Error parsing InfluxQL response: %s", e, exc_info=True)
            return {"sensors": {}, "error": f"Parse error: {str(e)}"}


    def analyze_query(self, query: str) -> str:
        """Process user query with LLM using sensor data"""
        sensor_data = self.get_sensor_data()

        if "error" in sensor_data:
            logger.error("Failed to get sensor data: %s", sensor_data["error"])
            return f"ERROR: Cannot access InfluxDB sensor data. {sensor_data['error']}. Please check InfluxDB configuration."

        if self.model_loaded:
            return self.generate_llm_response(query, sensor_data)
        else:
            logger.error("LLM model not loaded")
            return "Sorry, the AI model is not available. Please try again later."

    def generate_llm_response(self, query: str, sensor_data: Dict[str, Any]) -> str:
        """Generate response using CodeLlama with sensor data context"""
        try:
            # Create context with structured sensor data
            sensor_json = json.dumps(sensor_data.get('sensors', {}), indent=2)
            sensors_summary = self.create_sensor_summary(sensor_data)

            context_prompt = f"""You are an industrial IoT system analyst. You have access to real-time sensor data in JSON format.

CURRENT SENSOR DATA (JSON):
{sensor_json}

SUMMARY: {sensors_summary}

Analyze this structured sensor data and answer the user's question. Reference specific sensor IDs, values, and timestamps from the JSON data above."""

            # CodeLlama Instruct format
            chat_prompt = f"[INST] {context_prompt}\n\nUser Query: {query} [/INST]"

            # Tokenize and generate
            inputs = self.tokenizer(chat_prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    max_new_tokens=150,
                    temperature=0.1,
                    do_sample=True,
                    top_p=0.95,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            # Decode and clean response
            generated_tokens = outputs[0][len(inputs["input_ids"][0]):]
            response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

            if not response or len(response) < 5:
                return "I'm analyzing the sensor data. Could you rephrase your question?"

            return response

        except Exception as e:
            logger.error("LLM generation error: %s", e)
            return "Sorry, I'm having trouble processing your request right now. Please try again."

    def create_sensor_summary(self, sensor_data: Dict[str, Any]) -> str:
        """Create a brief sensor summary for LLM context"""
        if not sensor_data.get('sensors'):
            return "ERROR: No sensor data available - InfluxDB connection failed"

        sensors = sensor_data['sensors']
        sensor_types = {}
        anomaly_count = 0

        for data in sensors.values():
            sensor_type = data.get('type', 'unknown')
            sensor_types[sensor_type] = sensor_types.get(sensor_type, 0) + 1
            if data.get('is_anomaly', False):
                anomaly_count += 1

        # Create summary
        type_summary = [f"{count} {stype}" for stype, count in sensor_types.items()]

        detailed_summary = ", ".join(type_summary)
        status = f"Monitoring {len(sensors)} sensors: {detailed_summary}"

        if anomaly_count > 0:
            status += f" with {anomaly_count} anomalies detected"

        return status


    def run(self, host='0.0.0.0', port=8080):
        logger.info("Starting Edge LLM IoT ChatBot on port %d", port)
        self.app.run(host=host, port=port, debug=False)

def main():
    chatbot = EdgeLLMChatBot()
    chatbot.run()

if __name__ == '__main__':
    main()