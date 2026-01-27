#!/bin/bash
# Force complete removal and rebuild of backend - handles corrupted containers

set -e  # Exit on error

echo "=== FORCE REBUILD BACKEND ==="
echo ""

# Step 1: Stop backend
echo "1. Stopping backend..."
docker-compose -f docker-compose.production.yml -p bot-prod stop backend 2>/dev/null || true
sleep 2
echo "✓ Stopped"
echo ""

# Step 2: Remove ALL backend containers (by name pattern)
echo "2. Removing all backend containers..."
for container in $(docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}"); do
    echo "  Removing: $container"
    docker rm -f "$container" 2>/dev/null || true
done

# Also remove by partial name match
for container in $(docker ps -a --format "{{.ID}} {{.Names}}" | grep -E "backend|2c16a439cd05|805e07a3268c|0c3cae750d41" | awk '{print $1}'); do
    echo "  Removing orphaned: $container"
    docker rm -f "$container" 2>/dev/null || true
done
echo "✓ Containers removed"
echo ""

# Step 3: Clean Docker Compose state
echo "3. Cleaning Docker Compose state..."
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans 2>/dev/null || true
echo "✓ State cleaned"
echo ""

# Step 4: Build backend image
echo "4. Building backend image (this will take a few minutes)..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
if [ $? -ne 0 ]; then
    echo "✗ Build failed!"
    exit 1
fi
echo "✓ Build successful"
echo ""

# Step 5: Create and start backend (fresh, no recreate)
echo "5. Starting backend..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d backend
if [ $? -ne 0 ]; then
    echo "✗ Start failed!"
    exit 1
fi
echo "✓ Backend started"
echo ""

# Step 6: Wait and check health
echo "6. Waiting for backend to be ready..."
sleep 10
for i in {1..20}; do
    if docker exec bot-prod-backend curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✓ Backend is healthy"
        break
    fi
    echo "  Waiting... ($i/20)"
    sleep 3
done
echo ""

# Step 7: Check logs
echo "7. Checking router registration..."
echo ""
docker logs bot-prod-backend --tail 150 2>&1 | grep -E "router|import|registered|Successfully imported|Failed to import" || echo "No router logs found"
echo ""

# Step 8: Show status
echo "8. Container status:"
docker ps --filter "name=bot-prod-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== DONE ==="
echo ""
echo "Check full logs: docker logs bot-prod-backend --tail 200"
echo "Test endpoints: curl http://localhost:8000/api/v1/tickets/demo/tickets"
