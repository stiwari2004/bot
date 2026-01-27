#!/bin/bash
# Fix Docker state issue - removes orphaned containers and images
# Run this on the production server

set -e

echo "=== Fixing Docker State ==="
cd /opt/opsbot/bot

echo "1. Stopping all containers..."
docker-compose -f docker-compose.production.yml -p bot-prod down

echo "2. Removing old backend container..."
docker rm -f bot-prod-backend 2>/dev/null || true
docker rm -f f64072cf5289_bot-prod-backend 2>/dev/null || true

echo "3. Cleaning up dangling images..."
docker image prune -f

echo "4. Removing old backend images..."
docker images | grep bot-prod-backend | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true

echo "5. Rebuilding backend..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

echo "6. Starting services..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d

echo ""
echo "=== Docker state fixed ==="
echo "Check logs with: docker-compose -f docker-compose.production.yml -p bot-prod logs backend"
