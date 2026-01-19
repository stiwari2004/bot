#!/bin/bash
# Complete cleanup and rebuild of both production and dev environments

set -e

echo "🧹 Complete cleanup and rebuild of production and dev..."

# Step 1: Stop everything
echo "📦 Stopping all services..."
docker-compose -f docker-compose.production.yml stop 2>/dev/null || true
docker-compose -f docker-compose.dev.yml stop 2>/dev/null || true

# Step 2: Remove all bot containers (production and dev)
echo "🗑️  Removing all bot containers..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -i bot | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Step 3: Remove containers by specific patterns
echo "🗑️  Removing containers by name patterns..."
docker rm -f bot-proxy bot-prod-postgres bot-prod-redis bot-prod-backend bot-prod-frontend bot-prod-worker 2>/dev/null || true
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-frontend bot-dev-worker 2>/dev/null || true
docker rm -f bot_postgres_1 bot_redis_1 bot_backend_1 bot_frontend_1 bot_worker_1 2>/dev/null || true

# Step 4: Clean up dangling images
echo "🖼️  Cleaning up dangling images..."
docker image prune -f

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Rebuild production: docker-compose -f docker-compose.production.yml build"
echo "   2. Start production: docker-compose -f docker-compose.production.yml up -d"
echo "   3. Rebuild dev: docker-compose -f docker-compose.dev.yml build"
echo "   4. Start dev: docker-compose -f docker-compose.dev.yml up -d"
