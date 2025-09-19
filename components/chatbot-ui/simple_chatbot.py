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
        logger.info("Loading Qwen2.5-Coder-3B-Instruct (optimized for JSON and structured data analysis)...")

        # Initialize Qwen2.5-Coder 3B - faster and more efficient for edge deployment
        self.model_name = "Qwen/Qwen2.5-Coder-3B-Instruct"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            # Use GPU if available, fallback to CPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Using device: %s", device)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else "cpu",
                trust_remote_code=True
            )
            # Add pad token if needed
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            logger.info("Successfully loaded Qwen2.5-Coder-3B model")
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

    def generate_influxdb_query_with_llm(self, user_query: str) -> str:
        """Use Qwen to generate appropriate InfluxDB query based on user intent"""
        if not self.model_loaded:
            # Fallback to simple query if model not loaded
            return "SELECT * FROM sensor_data WHERE vessel_id = 'MV_FAIEMA_2025' ORDER BY time DESC LIMIT 500"

        try:
            schema_info = """
Database: sensors
Table: sensor_data
Vessel: MV FAIEMA 2025 Maritime Vessel

Columns:
- time: timestamp
- sensor_id: string (e.g., "engine_cylinder_temp_01", "oil_pressure_02", "cargo_temperature_03")
- sensor_type: string (maritime sensor types)
- value: float (sensor reading)
- unit: string (sensor unit)
- is_anomaly: boolean (true/false)
- vessel_id: string ("MV_FAIEMA_2025")
- location: string ("engine_room", "cargo_hold", "general")

Maritime Sensor Types:
Engine Room: engine_cylinder_temp, oil_pressure, oil_temperature, fuel_flow_rate, fuel_pressure, vibration_main, shaft_torque, shaft_rpm, bilge_level
Cargo Hold: cargo_temperature, cargo_humidity, o2_level, co2_level, ch4_level, cargo_weight, motion_sensor, water_ingress
Safety: fire_detector, smoke_detector

EXAMPLE QUERIES (copy format exactly):
- Engine temp status: SELECT MEAN(value), MAX(value), MIN(value) FROM sensor_data WHERE sensor_type = 'engine_cylinder_temp' AND vessel_id = 'MV_FAIEMA_2025' AND time > now() - 10m
- Recent oil pressure: SELECT value, time FROM sensor_data WHERE sensor_type = 'oil_pressure' AND vessel_id = 'MV_FAIEMA_2025' ORDER BY time DESC LIMIT 10
- All recent sensors: SELECT * FROM sensor_data WHERE vessel_id = 'MV_FAIEMA_2025' ORDER BY time DESC LIMIT 50

Always use vessel_id = 'MV_FAIEMA_2025' in WHERE clauses.
Common time filters:
- now() - 5m (last 5 minutes)
- now() - 1h (last hour)
- now() - 24h (last day)

Always use vessel_id = 'MV_FAIEMA_2025' in WHERE clauses.
"""

            messages = [
                {"role": "system", "content": f"""You are an InfluxDB query generator. Convert user questions into InfluxQL queries.

{schema_info}

Rules:
1. Always use InfluxQL syntax (not SQL)
2. Use time filters for recent data queries
3. Use GROUP BY for aggregations
4. Return ONLY the InfluxQL query, no explanation
5. Common patterns:
   - Averages: SELECT MEAN(value) FROM sensor_data WHERE time > now() - 10m AND sensor_type='temperature'
   - Counts: SELECT COUNT(*) FROM sensor_data WHERE time > now() - 10m
   - Recent data: SELECT * FROM sensor_data WHERE time > now() - 5m ORDER BY time DESC LIMIT 20
   - Anomalies: SELECT * FROM sensor_data WHERE is_anomaly=true AND time > now() - 10m"""},
                {"role": "user", "content": f"Generate InfluxQL query for: {user_query}"}
            ]

            # Apply chat template for Qwen
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                max_length=1024,
                truncation=True
            )

            # Move inputs to device
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.1,
                    do_sample=True,
                    top_p=0.9
                )

            # Decode the generated query
            generated_query = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

            # Clean up the query - remove any explanations, just get the SQL
            lines = generated_query.split('\n')
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SELECT'):
                    logger.info("LLM generated query: %s", line)
                    return line

            # If no SELECT found, return the first non-empty line
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    logger.info("LLM generated query: %s", line)
                    return line

            logger.warning("Could not extract query from LLM response: %s", generated_query)
            return "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 50"

        except Exception as e:
            logger.error("Error generating query with LLM: %s", e)
            return "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 50"

    def get_sensor_data(self, user_query: str = "") -> Dict[str, Any]:
        """Get sensor data from InfluxDB 1.8 using InfluxQL with LLM-generated queries"""
        try:
            # TEMPORARY WORKAROUND: Use hardcoded query for all maritime sensor data
            # Comment out LLM query generation for now
            # if user_query:
            #     influx_query = self.generate_influxdb_query_with_llm(user_query)
            #     logger.info("LLM generated InfluxDB query: %s", influx_query)
            # else:
            #     influx_query = "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 50"

            # Hardcoded query: all sensor data grouped by sensor type for last 12 hours
            # influx_query = "SELECT MEAN(value), MAX(value), MIN(value), COUNT(value) FROM sensor_data WHERE vessel_id = 'MV_FAIEMA_2025' AND time > now() - 12h GROUP BY sensor_type"
            influx_query = """SELECT value, unit, sensor_type, sensor_id FROM sensor_data
  WHERE vessel_id = 'MV_FAIEMA_2025'
    AND time > now() - 1h
    AND sensor_type =~ /^(engine_cylinder_temp|oil_pressure|vibration_main)$/
  GROUP BY sensor_type"""
            logger.info("Using hardcoded InfluxDB query: %s", influx_query)

            params = {
                'db': 'sensors',
                'q': influx_query
            }
            headers = {
                'Authorization': f'Token {self.influxdb_token}'
            }

            logger.debug("Making InfluxDB request: URL=%s, params=%s", f"{self.influxdb_url}/query", params)
            response = requests.get(f"{self.influxdb_url}/query", params=params, headers=headers, timeout=10)
            logger.debug("InfluxDB response: status=%d, content=%s", response.status_code, response.text[:500])

            if response.status_code == 200:
                result = self.parse_influxql_response(response.json())
                logger.info("Retrieved %d sensor records", len(result.get('sensors', {})))
                return result
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

            # Parse sensor data efficiently - handle both individual and aggregated data
            for serie_idx, serie in enumerate(series):
                columns = serie.get('columns', [])
                values = serie.get('values', [])
                tags = serie.get('tags', {})

                # Check if this is an aggregation result
                has_sensor_id = 'sensor_id' in columns
                is_aggregation = any(col in ['mean', 'max', 'min', 'count', 'sum'] for col in columns)

                for i, value_row in enumerate(values):
                    if len(value_row) == len(columns):
                        row_data = dict(zip(columns, value_row))

                        if is_aggregation and not has_sensor_id:
                            # Handle aggregation results - create virtual sensor entry
                            sensor_type = tags.get('sensor_type', 'all_sensors')
                            agg_type = next((k for k in row_data.keys() if k in ['mean', 'max', 'min', 'count', 'sum']), 'unknown')
                            agg_value = row_data.get(agg_type, 0)

                            sensor_id = f"{sensor_type}_{agg_type}_result"

                            sensors[sensor_id] = {
                                'id': sensor_id,
                                'type': sensor_type,
                                'value': float(agg_value) if agg_value is not None else 0.0,
                                'timestamp': row_data.get('time', ''),
                                'equipment_id': 'aggregated_result',
                                'location': 'system',
                                'is_anomaly': False,
                                'aggregation_type': agg_type
                            }
                        else:
                            # Handle individual sensor data
                            sensor_id = row_data.get('sensor_id', f'sensor_{serie_idx}_{i}')

                            sensors[sensor_id] = {
                                'id': sensor_id,
                                'type': row_data.get('sensor_type', 'unknown'),
                                'value': float(row_data.get('value', 0)) if row_data.get('value') is not None else 0.0,
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

    def _get_unit_for_sensor_type(self, sensor_type: str) -> str:
        """Get appropriate unit for sensor type"""
        unit_map = {
            'temperature': 'celsius',
            'pressure': 'kPa',
            'vibration': 'mm/s',
            'all_sensors': 'mixed'
        }
        return unit_map.get(sensor_type, 'unknown')

    def analyze_query(self, query: str) -> str:
        """Process user query with sensor data analysis"""
        sensor_data = self.get_sensor_data(query)

        if "error" in sensor_data:
            error_msg = sensor_data["error"]
            logger.error("Failed to get sensor data: %s", error_msg)
            return f"ERROR: Cannot access InfluxDB sensor data. {error_msg}. Please check InfluxDB configuration."

        # Use LLM to analyze sensor data
        if self.model_loaded:
            return self.generate_llm_response(query, sensor_data)
        else:
            return "Sorry, the AI model is not available. Please try again later."

    def analyze_maritime_sensors(self, query: str, sensor_data: Dict[str, Any]) -> str:
        """Simple rule-based analysis for maritime operational questions"""
        sensors = sensor_data.get('sensors', {})
        if not sensors:
            return "No sensor data available for analysis."

        query_lower = query.lower()

        # Engine cylinder temperature analysis
        if 'engine' in query_lower and 'cylinder' in query_lower and 'temperature' in query_lower:
            engine_temps = []
            for sensor_id, sensor in sensors.items():
                if sensor.get('type') == 'engine_cylinder_temp':
                    temp_value = sensor.get('value', 0)
                    engine_temps.append(temp_value)

            if engine_temps:
                avg_temp = sum(engine_temps) / len(engine_temps)
                max_temp = max(engine_temps)
                min_temp = min(engine_temps)

                if avg_temp <= 450:
                    status = "NORMAL" if avg_temp >= 300 else "LOW"
                elif avg_temp <= 500:
                    status = "WARNING"
                else:
                    status = "CRITICAL"

                return f"Engine Cylinder Temperature Status: {status}\n" \
                       f"Average: {avg_temp:.1f}°C (Normal: 300-450°C)\n" \
                       f"Range: {min_temp:.1f}°C to {max_temp:.1f}°C\n" \
                       f"Found {len(engine_temps)} engine cylinder sensors."
            else:
                return "No engine cylinder temperature sensors found in the current data."

        # General sensor overview
        sensor_types = {}
        for sensor in sensors.values():
            sensor_type = sensor.get('type', 'unknown')
            if sensor_type not in sensor_types:
                sensor_types[sensor_type] = []
            sensor_types[sensor_type].append(sensor.get('value', 0))

        summary = f"Maritime Vessel Sensor Summary (MV FAIEMA 2025):\n"
        for sensor_type, values in sensor_types.items():
            if values:
                avg_val = sum(values) / len(values)
                summary += f"- {sensor_type}: {len(values)} sensors, avg {avg_val:.1f}\n"

        return summary

    def generate_llm_response(self, query: str, sensor_data: Dict[str, Any]) -> str:
        """Generate response using Qwen2.5-Coder with sensor data context"""
        try:
            # Create sensor summary for LLM
            sensors_summary = self.create_sensor_summary(sensor_data)

            # Simplified prompt for cleaner responses
            messages = [
                {"role": "system", "content": f"""You are a maritime IoT analyst for MV FAIEMA 2025. Answer questions about sensor data.

SENSOR DATA: {sensors_summary}

OPERATIONAL LIMITS:
- Engine Cylinder Temperature: Normal 300-450°C, Warning >450°C, Critical >500°C
- Oil Pressure: Normal 300-500 kPa, Low <300 kPa, Critical <200 kPa
- Vibration: Normal <5 m/s, Warning 5-8 m/s, Critical >8 m/s

Answer in plain English. Be direct and concise."""},
                {"role": "user", "content": query}
            ]

            # Apply chat template for Qwen (following HuggingFace example)
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                max_length=2048,
                truncation=True
            )

            # Move inputs to device
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            logger.info("Input token count: %d", inputs["input_ids"].shape[-1])

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1
                )

            logger.info("Output token count: %d", len(outputs[0]))

            # Decode only the generated tokens (following HuggingFace example)
            response = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

            logger.info("Generated response: %s", response[:200])

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
