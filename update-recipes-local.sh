#!/bin/bash
set -e

echo "Updating component recipes for local development..."

# Local component server URL
COMPONENT_SERVER="http://component-server/components"

# Function to update recipe
update_recipe() {
    local component_name=$1
    local component_path=$2
    
    echo "Updating $component_name..."
    
    # Create backup
    cp "$component_path/recipe.json" "$component_path/recipe.json.backup"
    
    # Update URIs to use local component server
    sed -i "s|s3://BUCKET_NAME/COMPONENT_NAME/COMPONENT_VERSION|$COMPONENT_SERVER/$component_name/1.0.0|g" "$component_path/recipe.json"
    
    echo "  Updated $component_name recipe"
}

# Update all component recipes
update_recipe "com.edge.llm.SensorSimulator" "components/sensor-simulator"
update_recipe "com.edge.llm.ChatBotUI" "components/chatbot-ui"

echo ""
echo "Component recipes updated for local development!"
echo "Components will be served from: $COMPONENT_SERVER"
echo ""
echo "To revert to AWS URIs, restore from .backup files:"
echo "  find components -name 'recipe.json.backup' -exec bash -c 'mv \"\$1\" \"\${1%.backup}\"' _ {} \;"