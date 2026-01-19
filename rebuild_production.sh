#!/bin/bash
# Rebuild and start production environment

set -e

echo "🔨 Rebuilding production environment..."

# Step 1: Stop and remove production containers
echo "📦 Stopping production..."
docker-compose -f docker-compose.production.yml stop 2>/dev/null || true

# Step 2: Remove production containers
echo "🗑️  Removing production containers..."
docker-compose -f docker-compose.production.yml rm -f 2>/dev/null || true

# Also remove by name patterns
docker rm -f bot-prod-postgres bot-prod-redis bot-prod-backend bot-prod-frontend bot-prod-worker bot-proxy 2>/dev/null || true
docker rm -f bot_postgres_1 bot_redis_1 bot_backend_1 bot_frontend_1 bot_worker_1 2>/dev/null || true

# Step 3: Rebuild
echo "🔨 Building production images..."
docker-compose -f docker-compose.production.yml build

# Step 4: Start
echo "🚀 Starting production services..."
docker-compose -f docker-compose.production.yml up -d

echo ""
echo "✅ Production rebuild complete!"
echo ""
echo "📋 Checking status..."
docker-compose -f docker-compose.production.yml ps
