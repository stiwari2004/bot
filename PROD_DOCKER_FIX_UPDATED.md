# Production Docker Compose Fix - Updated Based on Actual Setup

## Understanding the Setup

From `docker-compose.production.yml`:
- **Container names are hardcoded**: `bot-prod-postgres`, `bot-prod-redis`, `bot-prod-backend`, `bot-prod-worker`, `bot-prod-frontend`, `bot-proxy`
- **Images are built** (not pulled from registry) - they get auto-named by docker-compose
- **Project name**: `bot-prod` (when using `-p bot-prod`)
- **Network**: `bot_app-network` (external, must exist)

## The Problem

The container `bot-prod-backend` references a Docker image that was deleted:
- Image SHA: `sha256:c7fb6f52722c20abd6efe377347ec5035fd3ca97afae43edca6b14002b344082`
- Container ID: `8a84501ec809` (short form) or full container name: `bot-prod-backend`

## Correct Fix Commands

### Step 1: Check Current Setup (Run on Server)

```bash
# See what containers exist
docker ps -a --filter "name=bot-prod" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"

# See what images exist
docker images | grep -E "(bot-prod|backend)"

# Check the problematic container
docker inspect bot-prod-backend 2>/dev/null | grep -E "(Image|ImageID)" || echo "Container not found"
```

### Step 2: Fix the Issue

```bash
# 1. Stop everything gracefully
docker-compose -f docker-compose.production.yml -p bot-prod down

# 2. Remove the corrupted backend container (by name, not ID)
docker rm -f bot-prod-backend

# 3. Remove any containers with missing images (safety check)
docker ps -a --format "{{.ID}} {{.Image}}" | while read container_id image; do
    if ! docker inspect "$image" >/dev/null 2>&1; then
        echo "Removing container $container_id (missing image: $image)"
        docker rm -f "$container_id"
    fi
done

# 4. Rebuild backend image (force rebuild to ensure fresh image)
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

# 5. Start everything
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

### One-Liner Fix

```bash
docker-compose -f docker-compose.production.yml -p bot-prod down && \
docker rm -f bot-prod-backend 2>/dev/null || true && \
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend && \
docker-compose -f docker-compose.production.yml -p bot-prod up -d
```

## Important Notes

1. **Container Names**: The compose file uses hardcoded container names (`bot-prod-backend`), so we remove by that name, not by project-generated names.

2. **Image Names**: Docker Compose will create images named like `bot-prod_backend`, `bot-prod_frontend`, etc. (project name + service name).

3. **Network**: The production compose file expects an external network `bot_app-network`. Make sure it exists:
   ```bash
   docker network inspect bot_app-network || docker network create bot_app-network
   ```

4. **Volumes**: Production uses `postgres_data` and `redis_data` volumes. These persist data, so don't remove them unless you want to lose data.

## If Network Doesn't Exist

```bash
# Create the network if it doesn't exist
docker network create bot_app-network 2>/dev/null || echo "Network already exists"
```

## Complete Fix Script

```bash
#!/bin/bash
set -e

echo "=== Fixing Production Docker Setup ==="

# Ensure network exists
echo "Checking network..."
docker network create bot_app-network 2>/dev/null || echo "Network exists"

# Stop and remove backend container
echo "Stopping containers..."
docker-compose -f docker-compose.production.yml -p bot-prod down

echo "Removing corrupted backend container..."
docker rm -f bot-prod-backend 2>/dev/null || true

# Clean up containers with missing images
echo "Cleaning up containers with missing images..."
docker ps -a --format "{{.ID}} {{.Image}}" | while read container_id image; do
    if ! docker inspect "$image" >/dev/null 2>&1; then
        echo "  Removing $container_id (image: $image)"
        docker rm -f "$container_id" 2>/dev/null || true
    fi
done

# Rebuild backend
echo "Rebuilding backend..."
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

# Start everything
echo "Starting services..."
docker-compose -f docker-compose.production.yml -p bot-prod up -d

echo "Done! Check status with: docker-compose -f docker-compose.production.yml -p bot-prod ps"
```
