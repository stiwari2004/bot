#!/bin/bash
# Complete Docker cleanup and restart script
# This will fix container state issues

# Don't exit on errors - continue through cleanup
set +e

echo "=== Complete Docker Cleanup and Fix ==="
echo ""

# 1. Stop all containers
echo "1. Stopping all containers..."
docker-compose -f docker-compose.production.yml stop 2>/dev/null || true

# 2. Remove all containers (force)
echo "2. Removing all containers..."
docker-compose -f docker-compose.production.yml rm -f 2>/dev/null || true

# 3. Remove the specific problematic containers
echo "3. Removing problematic containers..."
docker rm -f 84739eadab31_bot_frontend_1 2>/dev/null || true
docker rm -f bot_frontend_1 2>/dev/null || true
docker rm -f bot_backend_1 2>/dev/null || true

# 4. Remove orphaned containers
echo "4. Cleaning up orphaned containers..."
docker container prune -f

# 5. Remove dangling images
echo "5. Cleaning up dangling images..."
docker image prune -f

# 6. Remove the specific problematic image if it exists
echo "6. Checking for problematic images..."
docker images | grep "sha256:c645210c35d55378f49a3d9964bf8de3790d543e085826bb7b5b9ed549da2fc1" && \
    docker rmi sha256:c645210c35d55378f49a3d9964bf8de3790d543e085826bb7b5b9ed549da2fc1 2>/dev/null || true

# 7. Rebuild images (no cache to ensure fresh build)
echo "7. Rebuilding images..."
docker-compose -f docker-compose.production.yml build --no-cache

# 8. Start services
echo "8. Starting services..."
docker-compose -f docker-compose.production.yml up -d

# 9. Wait a bit for services to start
echo "9. Waiting for services to initialize..."
sleep 5

# 10. Check status
echo ""
echo "=== Service Status ==="
docker-compose -f docker-compose.production.yml ps

echo ""
echo "=== Done ==="
echo "Check logs with: docker-compose -f docker-compose.production.yml logs -f"

