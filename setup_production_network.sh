#!/bin/bash
# Create production network if it doesn't exist

NETWORK_NAME="bot_app-network"

echo "🔧 Setting up production network..."

# Check if network exists
if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "✅ Network '$NETWORK_NAME' already exists"
    docker network inspect "$NETWORK_NAME" --format='{{.Name}} - {{.Driver}}'
else
    echo "📦 Creating network '$NETWORK_NAME'..."
    docker network create "$NETWORK_NAME"
    if [ $? -eq 0 ]; then
        echo "✅ Network '$NETWORK_NAME' created successfully"
    else
        echo "❌ Failed to create network"
        exit 1
    fi
fi

echo ""
echo "📋 Network details:"
docker network inspect "$NETWORK_NAME" --format='Name: {{.Name}}
Driver: {{.Driver}}
Created: {{.Created}}
'

echo ""
echo "✅ Production network is ready!"
echo "You can now run: docker-compose -f docker-compose.production.yml up -d"
