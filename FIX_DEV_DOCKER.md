# Fix Docker Compose Dev Environment

## Problem
Container `9e71ec2fe0aa_bot-dev-backend` references a deleted image `sha256:b1617ebb41e154dbd49496921adb63b8a1606116a41682852df72bb2f40bcb0e`

## Solution

Run these commands in order:

```bash
# 1. Stop all services
docker-compose -f docker-compose.dev.yml -p bot-dev down

# 2. Remove the corrupted container
docker rm -f 9e71ec2fe0aa 2>/dev/null || true

# 3. Remove any other orphaned backend containers
docker ps -a --filter "name=bot-dev-backend" --format "{{.ID}}" | xargs -r docker rm -f

# 4. Remove orphaned containers
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans

# 5. Rebuild backend image (without cache to ensure clean build)
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend

# 6. Start services
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# 7. Check status
docker-compose -f docker-compose.dev.yml -p bot-dev ps
```

## Alternative: One-liner (if you're confident)

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans && \
docker rm -f 9e71ec2fe0aa 2>/dev/null || true && \
docker ps -a --filter "name=bot-dev-backend" --format "{{.ID}}" | xargs -r docker rm -f && \
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend && \
docker-compose -f docker-compose.dev.yml -p bot-dev up -d
```
