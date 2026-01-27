#!/bin/bash
# Fix production Docker image issue
# Run on server: srv640992

set -e

echo "=== Fixing production Docker containers ==="
cd /opt/opsbot/bot

echo "1. Stopping and removing old containers..."
docker-compose -f docker-compose.production.yml -p bot-prod down

echo "2. Removing old/dangling backend container if exists..."
docker rm -f bot-prod-backend 2>/dev/null || true

echo "3. Cleaning up dangling images..."
docker image prune -f

echo "4. Rebuilding backend image..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

echo "5. Starting all services..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d

echo "6. Waiting for services to start..."
sleep 10

echo "7. Checking backend logs..."
docker-compose -f docker-compose.production.yml -p bot-prod logs --tail=50 backend

echo ""
echo "=== Production containers should now be running ==="
echo "Check status with: docker-compose -f docker-compose.production.yml -p bot-prod ps"
