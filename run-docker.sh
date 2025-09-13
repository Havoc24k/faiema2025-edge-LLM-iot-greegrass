#!/bin/bash
set -e

echo "========================================="
echo "Edge LLM IoT - Local Docker Development"
echo "========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "🚀 Starting local Docker environment..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

# Show status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "========================================="
echo "🎉 Local Environment Ready!"
echo "========================================="
echo ""
echo "Access Points:"
echo "  💬 ChatBot Web UI: http://localhost:8080"
echo "  📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "  📈 InfluxDB UI: http://localhost:8086 (admin/admin123)"
echo ""
echo "🤖 ChatBot Capabilities:"
echo "  • 'List all available sensors'"
echo "  • 'What is the current system status?'"
echo "  • 'Show me temperature readings'"
echo "  • 'Are there any anomalies detected?'"
echo "  • 'Alert when temperature exceeds 65°C'"
echo ""
echo "Management:"
echo "  📋 View logs: docker-compose logs -f [service]"
echo "  🔄 Restart: docker-compose restart [service]"
echo "  🛑 Stop: docker-compose down"
echo ""
echo "🎯 This uses your existing components/ code directly - no duplication!"
echo ""