#!/bin/bash
# Comprehensive fix for both dev and prod environments

set -e

echo "🔧 Fixing both dev and prod environments..."

# 1. Stop all containers
echo "1. Stopping all containers..."
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.production.yml down --remove-orphans 2>/dev/null || true

# 2. Remove problematic containers
echo "2. Removing problematic containers..."
docker ps -a --filter "name=bot" --format "{{.ID}} {{.Names}}" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# 3. Clean up Docker
echo "3. Cleaning up Docker..."
docker container prune -f
# Don't prune networks - preserve bot_app-network

# 4. Rebuild dev backend
echo ""
echo "4. Rebuilding dev backend..."
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend

# 5. Start dev services
echo ""
echo "5. Starting dev services..."
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# 6. Wait for dev to start
echo ""
echo "6. Waiting for dev services to initialize..."
sleep 10

# 7. Check dev backend
echo ""
echo "7. Checking dev backend..."
docker logs bot-dev-backend --tail=20 2>&1 | tail -20 || echo "Dev backend not running"

# 8. Rebuild prod backend
echo ""
echo "8. Rebuilding production backend..."
docker-compose -f docker-compose.production.yml build --no-cache backend

# 9. Start prod services
echo ""
echo "9. Starting production services..."
docker-compose -f docker-compose.production.yml up -d

# 10. Wait for prod to start
echo ""
echo "10. Waiting for production services to initialize..."
sleep 10

# 11. Check prod backend
echo ""
echo "11. Checking production backend..."
docker logs bot_backend_1 --tail=20 2>&1 | tail -20 || echo "Prod backend not running"

# 12. Summary
echo ""
echo "=== Summary ==="
echo "Dev containers:"
docker ps --filter "name=bot-dev" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "Prod containers:"
docker ps --filter "name=bot_" --format "table {{.Names}}\t{{.Status}}" | grep -v "bot-dev"

echo ""
echo "✅ Done! Check logs if services aren't running:"
echo "  Dev:  docker logs bot-dev-backend --tail=50"
echo "  Prod: docker logs bot_backend_1 --tail=50"
