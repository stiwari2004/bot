#!/bin/bash
# Script to restore Docker networks for dev and production

set -e

echo "🔧 Restoring Docker networks..."

# 1. Create production network (external)
echo "1. Creating production network: bot_app-network"
docker network create bot_app-network --driver bridge 2>/dev/null || {
    if docker network inspect bot_app-network >/dev/null 2>&1; then
        echo "   ✅ Network bot_app-network already exists"
    else
        echo "   ❌ Failed to create bot_app-network"
        exit 1
    fi
}

# 2. Create dev network (if it doesn't exist)
echo "2. Creating dev network: bot_app-dev-network"
docker network create bot_app-dev-network --driver bridge 2>/dev/null || {
    if docker network inspect bot_app-dev-network >/dev/null 2>&1; then
        echo "   ✅ Network bot_app-dev-network already exists"
    else
        echo "   ❌ Failed to create bot_app-dev-network"
        exit 1
    fi
}

# 3. List all networks
echo ""
echo "3. Current networks:"
docker network ls | grep -E "bot_app|NAME"

echo ""
echo "✅ Networks restored!"
echo ""
echo "Now you can start services:"
echo "  Dev:      docker-compose -f docker-compose.dev.yml up -d"
echo "  Prod:     docker-compose -f docker-compose.production.yml up -d"
