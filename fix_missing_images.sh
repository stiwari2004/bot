#!/bin/bash
# Fix missing image/ContainerConfig errors for frontend and worker

echo "Removing problematic containers..."

# Remove containers by their IDs
docker rm -f dc4f18d03a52_bot-dev-frontend 1d80d23cad53_bot-dev-worker bot-dev-frontend bot-dev-worker 2>/dev/null || true

# Remove all containers with these names
docker ps -a --filter "name=frontend" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=worker" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo "Rebuilding images..."
docker-compose -f docker-compose.dev.yml build frontend worker

echo "Starting services..."
docker-compose -f docker-compose.dev.yml up -d frontend worker

echo "Done!"
