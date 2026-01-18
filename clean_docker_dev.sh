#!/bin/bash
# Complete Docker cleanup for dev environment - preserves networks only

set -e

echo "🧹 Starting complete Docker cleanup (preserving networks)..."

# Step 1: Stop all containers
echo "📦 Stopping all bot containers..."
docker-compose -f docker-compose.dev.yml stop || true
docker stop $(docker ps -q --filter "name=bot") 2>/dev/null || true

# Step 2: Remove all bot containers by name/id pattern
echo "🗑️  Removing all bot containers..."
docker ps -a --filter "name=bot" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker rm -f bot-dev-backend bot-dev-frontend bot-dev-worker bot-dev-postgres bot-dev-redis 2>/dev/null || true
docker rm -f bot_backend_1 bot_frontend_1 bot_worker_1 bot_postgres_1 bot_redis_1 2>/dev/null || true

# Step 3: Remove any containers with partial matches (the orphaned ones causing ContainerConfig errors)
echo "🔍 Removing orphaned containers..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -i bot | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Step 4: Clean up dangling/untagged images
echo "🖼️  Cleaning up dangling images..."
docker image prune -f

# Step 5: Remove bot-specific images (but keep base images)
echo "🗑️  Removing bot-specific images..."
docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | grep -E "bot|backend|frontend" | awk '{print $2}' | xargs -r docker rmi -f 2>/dev/null || true

# Step 6: Verify networks are preserved
echo "✅ Checking networks (should be preserved)..."
docker network ls | grep bot || echo "No bot networks found (will be created on next start)"

echo ""
echo "✅ Cleanup complete! Networks preserved."
echo ""
echo "📋 Next steps:"
echo "   1. Rebuild: docker-compose -f docker-compose.dev.yml build"
echo "   2. Start: docker-compose -f docker-compose.dev.yml up -d"
echo ""
