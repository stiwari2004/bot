#!/bin/bash
# Fix ALL container conflicts - remove by exact names

echo "=== FIXING ALL CONTAINER CONFLICTS ==="
echo ""

# Remove containers by exact names
echo "Removing containers..."
docker rm -f bot-prod-redis 2>/dev/null || true
docker rm -f bot-prod-postgres 2>/dev/null || true
docker rm -f bot-prod-backend 2>/dev/null || true
docker rm -f bot-prod-frontend 2>/dev/null || true
docker rm -f bot-prod-worker 2>/dev/null || true
docker rm -f bot-prod-proxy bot-proxy 2>/dev/null || true

# Remove by IDs from errors
docker rm -f 6db8e39880b5 728a9af896ba 2>/dev/null || true

# Remove all bot-prod containers
docker ps -a --filter "name=bot-prod" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo "✓ All containers removed"
echo ""

# Clean Docker Compose state
echo "Cleaning Docker Compose state..."
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans 2>/dev/null || true
echo "✓ State cleaned"
echo ""

# Build backend
echo "Building backend..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
echo "✓ Backend built"
echo ""

# Start all services
echo "Starting all services..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d
echo "✓ Services started"
echo ""

# Check status
sleep 5
docker ps --filter "name=bot-prod" --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "Checking backend logs..."
docker logs bot-prod-backend --tail 50 | grep -i "router\|import\|registered" || echo "No router logs yet"
