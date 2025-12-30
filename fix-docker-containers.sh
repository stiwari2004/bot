#!/bin/bash
# Fix Docker Compose container issues by cleaning up old containers

echo "=== Fixing Docker Compose Container Issues ==="
echo ""

# 1. Stop all containers
echo "1. Stopping all containers..."
docker-compose -f docker-compose.production.yml stop

# 2. Remove all containers (this will remove the problematic old container)
echo "2. Removing all containers..."
docker-compose -f docker-compose.production.yml rm -f

# 3. Remove orphaned containers
echo "3. Removing orphaned containers..."
docker container prune -f

# 4. Clean up any dangling images (optional, but helps)
echo "4. Cleaning up dangling images..."
docker image prune -f

# 5. Now rebuild and start
echo "5. Rebuilding and starting services..."
docker-compose -f docker-compose.production.yml up -d --build

echo ""
echo "=== Done ==="
echo "Check status with: docker-compose -f docker-compose.production.yml ps"
echo "Check logs with: docker-compose -f docker-compose.production.yml logs frontend --tail 50"

