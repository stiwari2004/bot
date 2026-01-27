#!/bin/bash
# Fix Docker Compose ContainerConfig Error
# This script cleans up corrupted containers and fixes the issue

set -e

echo "=== Fixing Docker Compose ContainerConfig Error ==="
echo ""

# Step 1: Stop all containers for the project
echo "Step 1: Stopping all containers..."
docker-compose -f docker-compose.dev.yml -p bot-prod down 2>/dev/null || true
docker-compose -f docker-compose.dev.yml -p bot-dev down 2>/dev/null || true

# Step 2: Remove orphaned containers
echo "Step 2: Removing orphaned containers..."
docker ps -a --filter "name=bot-" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Step 3: Remove corrupted containers that might be causing the issue
echo "Step 3: Removing potentially corrupted containers..."
docker ps -a --filter "name=bot-prod-redis" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=bot-prod-postgres" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=bot-dev-redis" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=bot-dev-postgres" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Step 4: Remove orphaned bot-proxy container
echo "Step 4: Removing orphaned bot-proxy container..."
docker ps -a --filter "name=bot-proxy" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Step 5: Clean up dangling images (optional but recommended)
echo "Step 5: Cleaning up dangling images..."
docker image prune -f 2>/dev/null || true

# Step 6: Verify volumes are clean (optional - comment out if you want to keep data)
# echo "Step 6: Removing volumes (WARNING: This will delete data)..."
# docker volume rm bot-prod_postgres_dev_data bot-prod_redis_dev_data 2>/dev/null || true
# docker volume rm bot-dev_postgres_dev_data bot-dev_redis_dev_data 2>/dev/null || true

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Now try running:"
echo "  docker-compose -f docker-compose.dev.yml -p bot-prod up -d --remove-orphans"
echo ""
echo "OR if you want to use dev project name:"
echo "  docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans"
