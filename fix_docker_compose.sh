#!/bin/bash
# Script to fix Docker Compose ContainerConfig errors
# Run this when you see 'ContainerConfig' KeyError

set -e

echo "🔧 Fixing Docker Compose ContainerConfig errors..."

# Stop all containers
echo "1. Stopping all containers..."
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Remove problematic containers
echo "2. Removing problematic containers..."
docker ps -a --filter "name=bot" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Prune containers
echo "3. Pruning stopped containers..."
docker container prune -f

# Prune system (removes unused images, networks, etc.)
# BUT preserve production network
echo "4. Pruning Docker system (preserving production network)..."
# Remove only unused networks, not the production one
docker network prune -f 2>/dev/null || true
# Don't remove bot_app-network
if docker network inspect bot_app-network >/dev/null 2>&1; then
    echo "   ✅ Preserved bot_app-network"
fi
# Prune other resources (images, containers)
docker system prune -f 2>/dev/null || true

# Remove specific images if they exist
echo "5. Removing old images..."
docker images --filter "reference=bot*backend*" --format "{{.ID}}" | xargs -r docker rmi -f 2>/dev/null || true

# Rebuild without cache
echo "6. Rebuilding backend image..."
docker-compose -f docker-compose.dev.yml build --no-cache backend

# Start services
echo "7. Starting services..."
docker-compose -f docker-compose.dev.yml up -d

echo "✅ Done! Check logs with: docker-compose -f docker-compose.dev.yml logs --tail=50 backend"
