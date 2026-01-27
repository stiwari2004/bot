#!/bin/bash
# Fix Docker Compose Production ContainerConfig Error
# This script removes corrupted containers and forces rebuild
# Based on actual setup: container names are hardcoded in docker-compose.production.yml

set -e

echo "=== Fixing Docker Compose Production ContainerConfig Error ==="
echo ""

# Step 1: Ensure network exists
echo "Step 1: Checking network..."
docker network create bot_app-network 2>/dev/null || echo "  Network bot_app-network already exists"

# Step 2: Stop all containers
echo "Step 2: Stopping all containers..."
docker-compose -f docker-compose.production.yml -p bot-prod down 2>/dev/null || true

# Step 3: Remove the corrupted backend container (by hardcoded name from compose file)
echo "Step 3: Removing corrupted backend container..."
docker rm -f bot-prod-backend 2>/dev/null || echo "  Container bot-prod-backend not found"

# Step 4: Remove any containers with missing images (safety check)
echo "Step 4: Checking for containers with missing images..."
docker ps -a --format "{{.ID}} {{.Image}}" | while read container_id image; do
    if ! docker inspect "$image" >/dev/null 2>&1; then
        echo "  Removing container $container_id (missing image: $image)"
        docker rm -f "$container_id" 2>/dev/null || true
    fi
done

# Step 5: Clean up dangling images
echo "Step 5: Cleaning up dangling images..."
docker image prune -f 2>/dev/null || true

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Now rebuild and start:"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod up -d"
echo ""
echo "OR rebuild all services:"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod up -d"
