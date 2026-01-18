#!/bin/bash
# Script to fix ContainerConfig Docker Compose issue
# This is a known issue with Docker Compose when container metadata gets corrupted

set -e

COMPOSE_FILE="${1:-docker-compose.dev.yml}"

echo "=========================================="
echo "Fixing ContainerConfig Issue"
echo "Using compose file: $COMPOSE_FILE"
echo "=========================================="
echo ""

echo "Step 1: Stopping all containers..."
docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

echo ""
echo "Step 2: Force removing ALL bot-related containers..."
# Remove containers by name pattern (more aggressive)
docker ps -a --format "{{.Names}} {{.ID}}" | grep -E "(bot|postgres|redis)" | awk '{print $2}' | xargs -r docker rm -f 2>/dev/null || true

# Also try removing by container name directly
for container in bot-dev-postgres bot-dev-redis bot_backend_1 bot_frontend_1 bot_worker_1 c02b8fa79685_bot_redis_1 520cc12f4ccb_bot_postgres_1 bot-proxy; do
    docker rm -f "$container" 2>/dev/null || true
done

echo ""
echo "Step 3: Removing corrupted images (forcing fresh pull)..."
# Get image names from compose file
IMAGES=$(docker-compose -f "$COMPOSE_FILE" config 2>/dev/null | grep -E "^\s+image:" | awk '{print $2}' | sort -u || echo "")

for image in $IMAGES; do
    if [ -n "$image" ]; then
        echo "  Removing image: $image"
        docker rmi -f "$image" 2>/dev/null || true
    fi
done

echo ""
echo "Step 4: Pruning Docker system (removing unused images/containers)..."
docker system prune -f

echo ""
echo "Step 5: Restarting Docker daemon (requires sudo)..."
echo "This step may require your password..."
if sudo systemctl restart docker 2>/dev/null; then
    echo "  Docker daemon restarted successfully"
else
    echo "  Warning: Could not restart Docker daemon. You may need to do this manually:"
    echo "    sudo systemctl restart docker"
    echo "  Continuing anyway..."
fi

echo ""
echo "Step 6: Waiting for Docker to be ready..."
sleep 5

# Verify Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker manually."
    exit 1
fi

echo ""
echo "Step 7: Pulling fresh images..."
docker-compose -f "$COMPOSE_FILE" pull --ignore-pull-failures || true

echo ""
echo "Step 8: Building services..."
docker-compose -f "$COMPOSE_FILE" build --no-cache 2>/dev/null || docker-compose -f "$COMPOSE_FILE" build || true

echo ""
echo "Step 9: Starting services with --force-recreate..."
# Use --force-recreate to bypass ContainerConfig check
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate || {
    echo "  Attempting alternative method: starting services individually..."
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate postgres || true
    sleep 2
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate redis || true
    sleep 2
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate backend || true
    sleep 2
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate worker || true
    sleep 2
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate frontend || true
}

echo ""
echo "Step 10: Waiting for services to be healthy..."
sleep 10

echo ""
echo "Step 11: Verifying containers are running..."
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "=========================================="
echo "Fix complete!"
echo "=========================================="
echo ""
echo "If containers are running, you can now run: ./run_tests.sh"
echo ""
echo "If issues persist, try:"
echo "  1. sudo systemctl restart docker"
echo "  2. docker system prune -a --volumes  # WARNING: Removes all unused data"
echo "  3. Re-run this script: ./fix_container_config_issue.sh [compose-file]"
