#!/bin/bash
# Fix Docker Compose dev environment - corrupted container with missing image

set -e

echo "=== Fixing Docker Compose Dev Environment ==="
echo ""

# Step 1: Stop all services
echo "1. Stopping all services..."
docker-compose -f docker-compose.dev.yml -p bot-dev down

# Step 2: Remove the corrupted backend container
echo ""
echo "2. Removing corrupted backend container..."
CONTAINER_ID="9e71ec2fe0aa"
if docker ps -a --format "{{.ID}}" | grep -q "^${CONTAINER_ID}$"; then
    docker rm -f ${CONTAINER_ID} 2>/dev/null || echo "Container ${CONTAINER_ID} already removed or doesn't exist"
else
    echo "Container ${CONTAINER_ID} not found"
fi

# Also try to remove by name pattern
docker ps -a --filter "name=bot-dev-backend" --format "{{.ID}}" | while read id; do
    if [ ! -z "$id" ]; then
        echo "Removing container: $id"
        docker rm -f $id 2>/dev/null || true
    fi
done

# Step 3: Remove orphaned containers
echo ""
echo "3. Removing orphaned containers..."
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans

# Step 4: Rebuild the backend image without cache
echo ""
echo "4. Rebuilding backend image (this may take a few minutes)..."
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend

# Step 5: Start services
echo ""
echo "5. Starting services..."
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

echo ""
echo "=== Done! ==="
echo "Check status with: docker-compose -f docker-compose.dev.yml -p bot-dev ps"
