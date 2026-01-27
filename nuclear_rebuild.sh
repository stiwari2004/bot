#!/bin/bash
# Nuclear option - remove EVERYTHING and rebuild from scratch

echo "=== NUCLEAR REBUILD - Removing ALL containers ==="
echo ""

# Step 1: Stop ALL services
echo "1. Stopping all services..."
docker-compose -f docker-compose.production.yml -p bot-prod stop 2>/dev/null || true
sleep 2
echo "✓ Stopped"
echo ""

# Step 2: Remove ALL containers for this project
echo "2. Removing ALL bot-prod containers..."
docker ps -a --filter "name=bot-prod" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
echo "✓ Removed"
echo ""

# Step 3: Remove containers by exact names
echo "3. Removing containers by exact names..."
docker rm -f bot-prod-redis bot-prod-postgres bot-prod-backend bot-prod-frontend bot-prod-worker bot-prod-proxy bot-proxy 2>/dev/null || true
echo "✓ Removed"
echo ""

# Step 4: Remove containers by IDs mentioned in errors
echo "4. Removing specific corrupted containers..."
docker rm -f 6db8e39880b5 728a9af896ba 2c16a439cd05 805e07a3268c 0c3cae750d41 e1010ac1538f 2>/dev/null || true
echo "✓ Removed"
echo ""

# Step 5: Clean Docker Compose state completely
echo "5. Cleaning Docker Compose state..."
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans 2>/dev/null || true
echo "✓ Cleaned"
echo ""

# Step 6: Verify no containers remain
echo "6. Verifying cleanup..."
REMAINING=$(docker ps -a --filter "name=bot-prod" --format "{{.Names}}" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠ Warning: Some containers still exist:"
    docker ps -a --filter "name=bot-prod" --format "{{.Names}}"
    echo "  Removing them..."
    docker ps -a --filter "name=bot-prod" --format "{{.ID}}" | xargs -r docker rm -f
fi
echo "✓ Cleanup verified"
echo ""

# Step 7: Build backend image
echo "7. Building backend image..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
if [ $? -ne 0 ]; then
    echo "✗ Build failed!"
    exit 1
fi
echo "✓ Build successful"
echo ""

# Step 8: Start ALL services fresh
echo "8. Starting all services..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d
if [ $? -ne 0 ]; then
    echo "✗ Start failed!"
    exit 1
fi
echo "✓ Services started"
echo ""

# Step 9: Wait and check
echo "9. Waiting for services..."
sleep 10
docker ps --filter "name=bot-prod" --format "table {{.Names}}\t{{.Status}}"
echo ""

# Step 10: Check backend logs
echo "10. Checking backend router registration..."
docker logs bot-prod-backend --tail 100 2>&1 | grep -E "router|import|registered|Successfully imported|Failed to import" || echo "No router logs yet"
echo ""

echo "=== DONE ==="
echo ""
echo "All services should be running. Check logs:"
echo "  docker logs bot-prod-backend --tail 200"
