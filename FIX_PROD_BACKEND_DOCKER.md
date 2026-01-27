# Fix Production Backend Docker Container Issue

## Problem
Container `4f4bc1743336_bot-prod-backend` references a deleted image `sha256:c4d01c0a2b0f14b201db95142a8021741b6fc7e7a731238436c385332f9d25b4`

## Solution

Run these commands:

```bash
# 1. Stop all services
docker-compose -f docker-compose.production.yml -p bot-prod down

# 2. Remove the corrupted backend container
docker rm -f 4f4bc1743336 2>/dev/null || true

# 3. Remove any other orphaned backend containers
docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}" | xargs -r docker rm -f

# 4. Remove orphaned containers
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans

# 5. Rebuild backend image (without cache to ensure clean build)
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

# 6. Start services
docker-compose -f docker-compose.production.yml -p bot-prod up -d

# 7. Check status
docker-compose -f docker-compose.production.yml -p bot-prod ps
```

## One-liner

```bash
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans && \
docker rm -f 4f4bc1743336 2>/dev/null || true && \
docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}" | xargs -r docker rm -f && \
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend && \
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```
