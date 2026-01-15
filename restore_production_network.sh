#!/bin/bash
# Script to restore the production Docker network

set -e

echo "🔧 Restoring production Docker network..."

# Check if network already exists
if docker network inspect bot_app-network >/dev/null 2>&1; then
    echo "✅ Network bot_app-network already exists"
    docker network inspect bot_app-network --format '{{.Name}} - {{.Driver}}'
else
    echo "Creating production network: bot_app-network"
    docker network create bot_app-network --driver bridge
    echo "✅ Network bot_app-network created successfully"
fi

echo ""
echo "Network details:"
docker network inspect bot_app-network --format 'Name: {{.Name}}
Driver: {{.Driver}}
ID: {{.Id}}
Created: {{.Created}}'

echo ""
echo "✅ Production network is ready!"
echo ""
echo "You can now start production services:"
echo "  docker-compose -f docker-compose.production.yml up -d"
