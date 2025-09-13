#!/bin/bash
set -e

echo "========================================="
echo "Edge LLM IoT Greengrass - Local Development"
echo "========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Update component recipes for local development
echo "📝 Updating component recipes for local development..."
./update-recipes-local.sh

echo ""
echo "🚀 Starting local Greengrass environment..."
echo ""

# Start the local Greengrass environment
docker-compose -f docker-compose-greengrass.yml up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Show status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose-greengrass.yml ps

echo ""
echo "========================================="
echo "🎉 Local Environment Ready!"
echo "========================================="
echo ""
echo "Access Points:"
echo "  📊 Grafana Dashboard: http://localhost:3000"
echo "     Default: admin / admin"
echo ""
echo "  💬 ChatBot Web UI: http://localhost:8080"
echo "     Interactive sensor queries"
echo ""
echo "  📈 InfluxDB UI: http://localhost:8086" 
echo "     Default: admin / admin123"
echo ""
echo "  🔧 Component Server: http://localhost:8090/components/"
echo "     Browse deployed components"
echo ""
echo "Management Commands:"
echo "  📋 View logs: docker-compose -f docker-compose-greengrass.yml logs -f [service]"
echo "  🔄 Restart: docker-compose -f docker-compose-greengrass.yml restart [service]"
echo "  🛑 Stop: docker-compose -f docker-compose-greengrass.yml down"
echo ""
echo "Greengrass Components Status:"
echo "  🌡️ Sensor Simulator: Generating dummy data every 5 seconds"
echo "  🤖 LLM Inference: Processing sensor data and chat requests"
echo "  💬 ChatBot UI: Ready for natural language queries"
echo "  📊 Telemetry Bridge: Forwarding data to Grafana/InfluxDB"
echo ""
echo "Try asking the ChatBot:"
echo "  • 'What is the current system status?'"
echo "  • 'Show me temperature readings'"
echo "  • 'Are there any anomalies detected?'"
echo "  • 'List all available sensors'"
echo ""