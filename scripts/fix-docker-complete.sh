#!/bin/bash
# Comprehensive Docker cleanup and rebuild script
# Fixes ContainerConfig errors and missing image issues

set -e

echo "=== Docker Cleanup Script ==="
echo "This will stop and remove all containers, then rebuild"

cd /opt/opsbot/bot || exit 1

# Stop all containers
echo "Stopping all containers..."
docker-compose -f docker-compose.production.yml stop || true

# Remove all containers (force)
echo "Removing all containers..."
docker-compose -f docker-compose.production.yml rm -f || true

# Remove specific problematic containers
echo "Removing orphaned containers..."
docker ps -a | grep bot_backend | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true
docker ps -a | grep f80add6d379c | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true

# Remove all bot images
echo "Removing old images..."
docker images | grep bot_backend | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
docker images | grep bot_frontend | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Prune system
echo "Pruning Docker system..."
docker system prune -f

# Rebuild backend
echo "Rebuilding backend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml build --no-cache backend

# Start services
echo "Starting services..."
docker-compose -f docker-compose.production.yml up -d

echo "=== Done ==="
echo "Check status with: docker-compose -f docker-compose.production.yml ps"

