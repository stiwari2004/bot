#!/bin/bash
# Complete cleanup and rebuild of production environment

set -e

echo "🧹 Complete cleanup and rebuild of production environment..."
echo ""

# Step 1: Stop all production containers
echo "📦 Stopping production containers..."
docker-compose -f docker-compose.production.yml stop 2>/dev/null || true

# Step 2: Remove all production containers
echo "🗑️  Removing production containers..."
docker-compose -f docker-compose.production.yml rm -f 2>/dev/null || true

# Step 3: Remove containers by name patterns (catch any stragglers)
echo "🧹 Removing containers by name patterns..."
docker rm -f bot-prod-postgres bot-prod-redis bot-prod-backend bot-prod-frontend bot-prod-worker bot-proxy 2>/dev/null || true
docker rm -f bot_postgres_1 bot_redis_1 bot_backend_1 bot_frontend_1 bot_worker_1 2>/dev/null || true

# Step 4: Remove production images (optional - uncomment if you want a complete rebuild)
# echo "🗑️  Removing production images..."
# docker rmi bot_frontend bot_backend 2>/dev/null || true

# Step 5: Prune any dangling containers/images
echo "🧹 Pruning dangling Docker resources..."
docker container prune -f 2>/dev/null || true

# Step 6: Create network if it doesn't exist
echo "🔧 Setting up production network..."
NETWORK_NAME="bot_app-network"
if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "✅ Network '$NETWORK_NAME' already exists"
else
    echo "📦 Creating network '$NETWORK_NAME'..."
    docker network create "$NETWORK_NAME" || true
    echo "✅ Network '$NETWORK_NAME' ready"
fi

# Step 7: Rebuild all images
echo "🔨 Building production images (no cache)..."
docker-compose -f docker-compose.production.yml build --no-cache

# Step 8: Start all services
echo "🚀 Starting production services..."
docker-compose -f docker-compose.production.yml up -d

echo ""
echo "✅ Production cleanup and rebuild complete!"
echo ""
echo "📋 Checking status..."
docker-compose -f docker-compose.production.yml ps

echo ""
echo "📊 Container health status:"
docker-compose -f docker-compose.production.yml ps --format json | jq -r '.[] | "\(.Name): \(.State) (\(.Health // "N/A"))"' 2>/dev/null || docker-compose -f docker-compose.production.yml ps
