#!/bin/bash
# Remove ALL conflicting bot containers - just containers, nothing else

echo "Removing all bot containers..."

# Remove by the specific IDs mentioned
docker rm -f a58e74494fb1ec4abd25a4998186f3d47b05efb2e2b36dc65e0e471f1f2ba0ca 2>/dev/null || true

# Remove all bot containers by name pattern
docker ps -a --filter "name=bot" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Also remove by exact names
docker rm -f bot-dev-backend bot-dev-frontend bot-dev-worker bot_backend_1 bot_frontend_1 bot_worker_1 2>/dev/null || true

echo "Done. Now try: docker-compose -f docker-compose.dev.yml up -d"
