# Build Dev Frontend (Fix BuildKit Permission Error)

## The Issue
Docker BuildKit is trying to create `/home/opsadmin` during the build, causing permission errors.

## Solution: Disable BuildKit

```bash
# Build frontend without BuildKit
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.dev.yml -p bot-dev build frontend

# Start frontend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d frontend

# Check logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs frontend | tail -30
```

## Alternative: If Still Failing

If the above doesn't work, try removing any cached build data:

```bash
# Remove old frontend container
docker-compose -f docker-compose.dev.yml -p bot-dev stop frontend
docker rm -f bot-dev-frontend 2>/dev/null || true

# Remove frontend image
docker rmi bot-dev_frontend:latest 2>/dev/null || true

# Build fresh without BuildKit
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache frontend

# Start frontend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d frontend
```

