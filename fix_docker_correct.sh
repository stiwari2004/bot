#!/bin/bash
# Fix Docker Compose - Dynamic detection of containers
# This script automatically detects and fixes the actual container setup

set -e

echo "=== Docker Compose Fix - Auto Detection ==="
echo ""

# Detect which containers exist
BACKEND_CONTAINER=$(docker ps -a --filter "name=backend" --format "{{.Names}}" | head -1)
POSTGRES_CONTAINER=$(docker ps -a --filter "name=postgres" --format "{{.Names}}" | head -1)
REDIS_CONTAINER=$(docker ps -a --filter "name=redis" --format "{{.Names}}" | head -1)
FRONTEND_CONTAINER=$(docker ps -a --filter "name=frontend" --format "{{.Names}}" | head -1)
WORKER_CONTAINER=$(docker ps -a --filter "name=worker" --format "{{.Names}}" | head -1)

echo "Detected containers:"
echo "  Backend: ${BACKEND_CONTAINER:-NOT FOUND}"
echo "  Postgres: ${POSTGRES_CONTAINER:-NOT FOUND}"
echo "  Redis: ${REDIS_CONTAINER:-NOT FOUND}"
echo "  Frontend: ${FRONTEND_CONTAINER:-NOT FOUND}"
echo "  Worker: ${WORKER_CONTAINER:-NOT FOUND}"
echo ""

# Detect compose file
if [ -f "docker-compose.production.yml" ]; then
    COMPOSE_FILE="docker-compose.production.yml"
    echo "Using: docker-compose.production.yml"
elif [ -f "docker-compose.dev.yml" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    echo "Using: docker-compose.dev.yml"
else
    echo "ERROR: No docker-compose file found!"
    exit 1
fi

# Detect project name from container names
if [[ "$BACKEND_CONTAINER" == *"prod"* ]]; then
    PROJECT_NAME="bot-prod"
    echo "Detected project: bot-prod"
elif [[ "$BACKEND_CONTAINER" == *"dev"* ]]; then
    PROJECT_NAME="bot-dev"
    echo "Detected project: bot-dev"
else
    # Try to detect from compose file
    if [[ "$COMPOSE_FILE" == *"production"* ]]; then
        PROJECT_NAME="bot-prod"
    else
        PROJECT_NAME="bot-dev"
    fi
    echo "Using project: $PROJECT_NAME (from compose file)"
fi

echo ""
echo "=== Fixing Docker Setup ==="
echo ""

# Step 1: Stop everything
echo "Step 1: Stopping containers..."
docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down 2>/dev/null || true

# Step 2: Remove backend container if it exists
if [ -n "$BACKEND_CONTAINER" ]; then
    echo "Step 2: Removing backend container: $BACKEND_CONTAINER"
    docker rm -f "$BACKEND_CONTAINER" 2>/dev/null || true
fi

# Step 3: Remove any containers with missing images
echo "Step 3: Checking for containers with missing images..."
docker ps -a --format "{{.ID}} {{.Image}}" | while read -r container_id image; do
    if ! docker inspect "$image" >/dev/null 2>&1; then
        echo "  Removing container $container_id (missing image: $image)"
        docker rm -f "$container_id" 2>/dev/null || true
    fi
done

# Step 4: Remove all containers for this project
echo "Step 4: Removing all project containers..."
if [ -n "$BACKEND_CONTAINER" ]; then
    docker ps -a --filter "name=${PROJECT_NAME}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
fi

# Step 5: Clean up dangling images
echo "Step 5: Cleaning up dangling images..."
docker image prune -f 2>/dev/null || true

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Detected setup:"
echo "  Compose file: $COMPOSE_FILE"
echo "  Project name: $PROJECT_NAME"
echo ""
echo "Now rebuild and start:"
echo "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache backend"
echo "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d"
echo ""
echo "OR rebuild all services:"
echo "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache"
echo "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d"
