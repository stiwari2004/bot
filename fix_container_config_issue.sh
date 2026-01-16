#!/bin/bash
# Script to fix ContainerConfig Docker Compose issue
# This is a known issue with Docker Compose when container metadata gets corrupted

set -e

COMPOSE_FILE="docker-compose.dev.yml"

echo "=========================================="
echo "Fixing ContainerConfig Issue"
echo "=========================================="
echo ""

echo "Step 1: Stopping all containers..."
docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

echo ""
echo "Step 2: Removing orphaned containers..."
# Find and remove any containers with the project name
docker ps -a --filter "name=bot" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo ""
echo "Step 3: Cleaning up Docker volumes (optional - uncomment if needed)..."
# Uncomment the next line if you want to remove volumes (WARNING: This deletes data)
# docker volume ls --filter "name=bot" --format "{{.Name}}" | xargs -r docker volume rm 2>/dev/null || true

echo ""
echo "Step 4: Restarting Docker daemon (requires sudo)..."
echo "This step may require your password..."
sudo systemctl restart docker || {
    echo "Warning: Could not restart Docker daemon. You may need to do this manually:"
    echo "  sudo systemctl restart docker"
}

echo ""
echo "Step 5: Waiting for Docker to be ready..."
sleep 5

echo ""
echo "Step 6: Starting services..."
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Step 7: Waiting for services to be healthy..."
sleep 10

echo ""
echo "Step 8: Verifying containers are running..."
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "=========================================="
echo "Fix complete!"
echo "=========================================="
echo ""
echo "If containers are running, you can now run: ./run_tests.sh"
