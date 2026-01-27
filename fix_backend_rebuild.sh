#!/bin/bash
# Fix corrupted backend container and rebuild with new code

echo "=== Fixing Backend Container and Rebuilding ==="
echo ""

# Step 1: Stop the backend service
echo "1. Stopping backend service..."
docker-compose -f docker-compose.production.yml -p bot-prod stop backend 2>/dev/null || true
echo "✓ Backend stopped"
echo ""

# Step 2: Remove the corrupted backend container
echo "2. Removing corrupted backend container..."
CONTAINER_ID=$(docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}" | head -1)
if [ ! -z "$CONTAINER_ID" ]; then
    echo "Found container: $CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" 2>/dev/null || true
    echo "✓ Container removed"
else
    echo "No container found to remove"
fi
echo ""

# Step 3: Remove orphaned containers with similar names
echo "3. Cleaning up orphaned containers..."
docker ps -a --filter "name=backend" --format "{{.ID}}" | while read id; do
    if [ ! -z "$id" ]; then
        echo "Removing orphaned container: $id"
        docker rm -f "$id" 2>/dev/null || true
    fi
done
echo "✓ Cleanup complete"
echo ""

# Step 4: Build the backend image
echo "4. Building backend image..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
if [ $? -eq 0 ]; then
    echo "✓ Backend image built successfully"
else
    echo "✗ Backend build failed"
    exit 1
fi
echo ""

# Step 5: Start the backend service
echo "5. Starting backend service..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d backend
if [ $? -eq 0 ]; then
    echo "✓ Backend started successfully"
else
    echo "✗ Backend start failed"
    exit 1
fi
echo ""

# Step 6: Wait for backend to be healthy
echo "6. Waiting for backend to be healthy..."
sleep 5
for i in {1..30}; do
    if docker exec bot-prod-backend curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✓ Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠ Backend may not be fully ready yet"
    else
        echo "  Waiting... ($i/30)"
        sleep 2
    fi
done
echo ""

# Step 7: Check logs for router registration
echo "7. Checking router registration logs..."
echo ""
docker logs bot-prod-backend --tail 50 | grep -i "router\|import\|registered" || echo "No router logs found yet"
echo ""

echo "=== Done ==="
echo ""
echo "Backend should now be running with the updated code."
echo "Check logs with: docker logs bot-prod-backend --tail 100"
