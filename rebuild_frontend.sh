#!/bin/bash
# Completely remove and rebuild frontend container

echo "Removing old frontend container..."
docker rm -f d665c73cb4a1_bot-dev-frontend bot-dev-frontend 2>/dev/null || true

echo "Finding all frontend containers..."
docker ps -a --filter "name=frontend" --format "{{.ID}} {{.Names}}" | xargs -r echo || true
docker ps -a --filter "name=frontend" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo "Removing old frontend image (if needed)..."
docker images | grep -E "bot.*frontend|frontend.*bot" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true

echo "Building fresh frontend image..."
docker-compose -f docker-compose.dev.yml build frontend

echo "Starting frontend..."
docker-compose -f docker-compose.dev.yml up -d frontend

echo "Done!"
