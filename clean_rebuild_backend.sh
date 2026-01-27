#!/bin/bash
# Complete cleanup and rebuild of backend container

echo "=== Complete Backend Cleanup and Rebuild ==="
echo ""

# Step 1: Stop backend service
echo "1. Stopping backend service..."
docker-compose -f docker-compose.production.yml -p bot-prod stop backend 2>/dev/null || true
echo "✓ Backend stopped"
echo ""

# Step 2: Find and remove ALL backend containers
echo "2. Removing all backend containers..."
CONTAINER_IDS=$(docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}")
if [ ! -z "$CONTAINER_IDS" ]; then
    echo "$CONTAINER_IDS" | while read id; do
        if [ ! -z "$id" ]; then
            echo "  Removing container: $id"
            docker rm -f "$id" 2>/dev/null || true
        fi
    done
    echo "✓ All backend containers removed"
else
    echo "  No backend containers found"
fi
echo ""

# Step 3: Remove orphaned containers
echo "3. Removing orphaned containers..."
docker ps -a --filter "name=backend" --format "{{.ID}}" | while read id; do
    if [ ! -z "$id" ]; then
        echo "  Removing orphaned container: $id"
        docker rm -f "$id" 2>/dev/null || true
    fi
done
echo "✓ Orphaned containers removed"
echo ""

# Step 4: Clean up Docker Compose state
echo "4. Cleaning Docker Compose state..."
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans 2>/dev/null || true
echo "✓ Docker Compose state cleaned"
echo ""

# Step 5: Remove backend image (optional - uncomment if you want to force rebuild)
# echo "5. Removing old backend image..."
# docker images | grep "bot-prod.*backend\|backend" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
# echo "✓ Old images removed"
# echo ""

# Step 6: Build backend image from scratch
echo "5. Building backend image (this may take a few minutes)..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
if [ $? -eq 0 ]; then
    echo "✓ Backend image built successfully"
else
    echo "✗ Backend build failed"
    exit 1
fi
echo ""

# Step 7: Start backend service
echo "6. Starting backend service..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d backend
if [ $? -eq 0 ]; then
    echo "✓ Backend started successfully"
else
    echo "✗ Backend start failed"
    exit 1
fi
echo ""

# Step 8: Wait for backend to be healthy
echo "7. Waiting for backend to be healthy..."
sleep 5
for i in {1..30}; do
    if docker exec bot-prod-backend curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✓ Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠ Backend may not be fully ready yet (checking logs...)"
    else
        echo "  Waiting... ($i/30)"
        sleep 2
    fi
done
echo ""

# Step 9: Check logs for router registration
echo "8. Checking router registration logs..."
echo ""
docker logs bot-prod-backend --tail 100 2>&1 | grep -i "router\|import\|registered\|successfully imported" || echo "No router logs found - check full logs"
echo ""

# Step 10: Show container status
echo "9. Container status:"
docker ps --filter "name=bot-prod-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== Done ==="
echo ""
echo "If routers are registered, you should see:"
echo "  - 'Successfully imported Phase 2 endpoints'"
echo "  - 'Registered ticket_ingestion router'"
echo "  - 'Registered agent_execution router'"
echo "  - 'Registered alerts router'"
echo "  - 'Registered change_tickets router'"
echo ""
echo "Check full logs with: docker logs bot-prod-backend --tail 200"
