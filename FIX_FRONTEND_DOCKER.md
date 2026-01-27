# Fix Frontend Docker Container Issue

## Problem
Container `a9a467d8d3d2_bot-dev-frontend` references a deleted image `sha256:9993bba437245891c6c586594891ff39268b201c07cf70a32f1ee9fb4addcdee`

## Solution

Run these commands:

```bash
# 1. Stop all services
docker-compose -f docker-compose.dev.yml -p bot-dev down

# 2. Remove the corrupted frontend container
docker rm -f a9a467d8d3d2 2>/dev/null || true

# 3. Remove any other orphaned frontend containers
docker ps -a --filter "name=bot-dev-frontend" --format "{{.ID}}" | xargs -r docker rm -f

# 4. Remove orphaned containers
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans

# 5. Rebuild frontend image (without cache to ensure clean build)
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache frontend

# 6. Start services
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# 7. Check status
docker-compose -f docker-compose.dev.yml -p bot-dev ps
```

## One-liner

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans && \
docker rm -f a9a467d8d3d2 2>/dev/null || true && \
docker ps -a --filter "name=bot-dev-frontend" --format "{{.ID}}" | xargs -r docker rm -f && \
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache frontend && \
docker-compose -f docker-compose.dev.yml -p bot-dev up -d
```
