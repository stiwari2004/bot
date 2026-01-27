# Production Docker Compose Fix - ContainerConfig Error

## Problem
The container `bot-prod-backend` references a Docker image that no longer exists:
- Image SHA: `sha256:c7fb6f52722c20abd6efe377347ec5035fd3ca97afae43edca6b14002b344082`
- Docker Compose tries to inspect the old container's image config but fails

## Quick Fix Commands

### Option 1: Remove Container and Rebuild (Recommended)

```bash
# 1. Stop everything
docker-compose -f docker-compose.production.yml -p bot-prod down

# 2. Remove the corrupted backend container
docker rm -f bot-prod-backend 8a84501ec809_bot-prod-backend

# 3. Remove any containers referencing the missing image
docker ps -a --format "{{.ID}} {{.Image}}" | grep "c7fb6f52722c20abd6efe377347ec5035fd3ca97afae43edca6b14002b344082" | awk '{print $1}' | xargs docker rm -f

# 4. Rebuild the backend image (force rebuild)
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

# 5. Start everything
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

### Option 2: Use the Fix Script

```bash
# Make script executable
chmod +x fix_prod_docker.sh

# Run the fix script
./fix_prod_docker.sh

# Then rebuild and start
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

### Option 3: Complete Clean Rebuild (If above doesn't work)

```bash
# 1. Stop and remove everything
docker-compose -f docker-compose.production.yml -p bot-prod down

# 2. Remove all bot-prod containers
docker ps -a --filter "name=bot-prod" -q | xargs docker rm -f

# 3. Remove backend image if it exists (optional)
docker images | grep bot-prod-backend | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# 4. Rebuild all services
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache

# 5. Start everything
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

## One-Liner Quick Fix

```bash
docker-compose -f docker-compose.production.yml -p bot-prod down && \
docker rm -f bot-prod-backend 8a84501ec809_bot-prod-backend 2>/dev/null || true && \
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend && \
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

## Why This Happens

1. **Image was deleted**: The Docker image was removed (maybe by `docker image prune` or manual deletion)
2. **Container still references it**: The old container still has metadata pointing to the deleted image
3. **Docker Compose tries to inspect**: When recreating, it tries to read the old container's image config but fails

## Prevention

- Don't manually delete images that are in use by containers
- Use `docker-compose down` before cleaning images
- Consider using image tags instead of relying on SHA references
