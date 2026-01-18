#!/bin/bash
# Fix frontend container ContainerConfig error

echo "Removing conflicting frontend container..."

# Remove frontend container by name
docker rm -f bot-dev-frontend 2>/dev/null || true

# Find and remove any other frontend containers
docker ps -a --filter "name=frontend" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

echo "Done. Now run: docker-compose -f docker-compose.dev.yml up -d frontend"
