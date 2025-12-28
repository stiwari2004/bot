#!/bin/bash
# Create Docker network for production compose file
# This fixes the "network not found" error

set -e

NETWORK_NAME="bot_app-network"

echo "🌐 Creating Docker network: $NETWORK_NAME"
echo ""

# Check if network exists
if docker network ls | grep -q "$NETWORK_NAME"; then
    echo "✅ Network '$NETWORK_NAME' already exists"
    docker network inspect $NETWORK_NAME | grep -A 5 "Name"
else
    echo "📦 Creating network '$NETWORK_NAME'..."
    docker network create $NETWORK_NAME
    echo "✅ Network created successfully"
fi

echo ""
echo "📊 Network details:"
docker network inspect $NETWORK_NAME --format '{{.Name}}: {{.Driver}} ({{.Scope}})'

echo ""
echo "✅ Network is ready for docker-compose.production.yml"

