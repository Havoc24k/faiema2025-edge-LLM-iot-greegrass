class ChatBotUI {
    constructor() {
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isConnected = false;
        
        this.initializeUI();
        this.connectWebSocket();
        this.loadSensorSummary();
        
        // Auto-refresh sensor summary every 30 seconds
        setInterval(() => this.loadSensorSummary(), 30000);
    }
    
    initializeUI() {
        // Add event listeners
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        sendButton.addEventListener('click', () => this.sendMessage());
        
        // Focus on input
        messageInput.focus();
        
        // Load chat history
        this.loadChatHistory();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            
            setTimeout(() => {
                console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connectWebSocket();
            }, delay);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connectionStatus');
        const statusText = document.getElementById('statusText');
        
        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = this.reconnectAttempts > 0 ? 'Reconnecting...' : 'Disconnected';
        }
    }
    
    handleWebSocketMessage(data) {
        if (data.type === 'response') {
            this.addMessage(data.message, 'assistant', data.timestamp);
        }
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        messageInput.value = '';
        
        // Disable send button temporarily
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = true;
        
        try {
            // Send via REST API (more reliable than WebSocket for important messages)
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });
            
            if (response.ok) {
                const data = await response.json();
                this.addMessage(data.message, 'assistant', data.timestamp);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage(
                'I apologize, but I encountered an error processing your message. Please try again.',
                'assistant'
            );
        } finally {
            sendButton.disabled = false;
            messageInput.focus();
        }
    }
    
    addMessage(text, sender, timestamp = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatarIcon = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessage(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Update recent activity
        this.updateRecentActivity(`${sender === 'user' ? 'User' : 'Assistant'}: ${text.substring(0, 50)}${text.length > 50 ? '...' : ''}`);
    }
    
    formatMessage(text) {
        // Convert URLs to links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
        
        // Convert line breaks to HTML
        text = text.replace(/\n/g, '<br>');
        
        // Highlight anomaly keywords
        const anomalyKeywords = ['anomaly', 'alert', 'warning', 'critical', 'error'];
        anomalyKeywords.forEach(keyword => {
            const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
            text = text.replace(regex, `<span style="color: var(--warning-color); font-weight: bold;">${keyword}</span>`);
        });
        
        return text;
    }
    
    updateRecentActivity(activity) {
        const activityList = document.getElementById('recentActivity');
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        
        const now = new Date();
        activityItem.innerHTML = `
            <span class="activity-time">${now.toLocaleTimeString()}</span>
            <span class="activity-text">${activity}</span>
        `;
        
        // Add to top of list
        activityList.insertBefore(activityItem, activityList.firstChild);
        
        // Keep only last 10 items
        while (activityList.children.length > 10) {
            activityList.removeChild(activityList.lastChild);
        }
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch('/chat-history');
            if (response.ok) {
                const data = await response.json();
                const history = data.history || [];
                
                // Clear existing messages except welcome message
                const messagesContainer = document.getElementById('chatMessages');
                const welcomeMessage = messagesContainer.querySelector('.message.assistant');
                messagesContainer.innerHTML = '';
                if (welcomeMessage) {
                    messagesContainer.appendChild(welcomeMessage);
                }
                
                // Add history messages
                history.forEach(msg => {
                    this.addMessage(msg.message, msg.type, msg.timestamp);
                });
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    
    async loadSensorSummary() {
        try {
            const response = await fetch('/sensor-summary');
            if (response.ok) {
                const data = await response.json();
                this.updateSensorStatus(data);
            }
        } catch (error) {
            console.error('Error loading sensor summary:', error);
        }
    }
    
    updateSensorStatus(data) {
        if (data.sensor_summary) {
            const summary = data.sensor_summary;
            
            // Update temperature
            if (summary.temperature) {
                const temp = summary.temperature;
                document.getElementById('tempStatus').textContent = 
                    `${temp.avg_value}${temp.unit} (${temp.count} readings)`;
            }
            
            // Update pressure
            if (summary.pressure) {
                const pressure = summary.pressure;
                document.getElementById('pressureStatus').textContent = 
                    `${pressure.avg_value}${pressure.unit} (${pressure.count} readings)`;
            }
            
            // Update vibration
            if (summary.vibration) {
                const vibration = summary.vibration;
                document.getElementById('vibrationStatus').textContent = 
                    `${vibration.avg_value}${vibration.unit} (${vibration.count} readings)`;
            }
            
            // Update anomaly count
            document.getElementById('anomalyCount').textContent = data.anomaly_count || 0;
            
            // Update activity
            this.updateRecentActivity(`Sensor data updated: ${data.total_readings} readings, ${data.anomaly_count} anomalies`);
        } else if (data.message) {
            // No data available
            document.getElementById('tempStatus').textContent = '--';
            document.getElementById('pressureStatus').textContent = '--';
            document.getElementById('vibrationStatus').textContent = '--';
            document.getElementById('anomalyCount').textContent = '--';
        }
    }
}

// Quick message functions
function sendQuickMessage(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    chatBot.sendMessage();
}

// Initialize when page loads
let chatBot;
document.addEventListener('DOMContentLoaded', () => {
    chatBot = new ChatBotUI();
});