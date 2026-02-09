# Docker Compose ContainerConfig Error - Fix Guide

## Problem
The error `KeyError: 'ContainerConfig'` occurs when Docker Compose tries to recreate containers but encounters corrupted container metadata or orphaned containers.

## Quick Fix (Run these commands on the server)

### Option 1: Clean and Restart (Recommended)

```bash
# 1. Stop all containers
docker-compose -f docker-compose.dev.yml -p bot-prod down --remove-orphans

# 2. Remove orphaned/corrupted containers
docker ps -a --filter "name=bot-" -q | xargs docker rm -f 2>/dev/null || true

# 3. Remove the specific problematic containers
docker rm -f bot-prod-redis bot-prod-postgres bot-proxy 2>/dev/null || true

# 4. Clean up dangling images
docker image prune -f

# 5. Start fresh
docker-compose -f docker-compose.dev.yml -p bot-prod up -d --remove-orphans
```

### Option 2: Use the Fix Script

```bash
# Make script executable
chmod +x fix_docker_compose.sh

# Run the fix script
./fix_docker_compose.sh

# Then start containers
docker-compose -f docker-compose.dev.yml -p bot-prod up -d --remove-orphans
```

### Option 3: Nuclear Option (If above doesn't work - DELETES DATA)

```bash
# WARNING: This will delete all container data!

# Stop everything
docker-compose -f docker-compose.dev.yml -p bot-prod down -v --remove-orphans

# Remove all bot-related containers
docker ps -a --filter "name=bot-" -q | xargs docker rm -f

# Remove volumes (DELETES DATA)
docker volume ls | grep bot | awk '{print $2}' | xargs docker volume rm

# Start fresh
docker-compose -f docker-compose.dev.yml -p bot-prod up -d
```

## Important Notes

1. **Project Name Mismatch**: You're using `-p bot-prod` but the compose file is configured for dev. Consider:
   - Use `-p bot-dev` for dev environment
   - OR create a `docker-compose.prod.yml` file for production

2. **Orphaned Containers**: The warning about `bot-proxy` suggests there are orphaned containers. Use `--remove-orphans` flag.

3. **Volume Persistence**: If you want to keep your database data, DON'T use `-v` flag in `docker-compose down`.

## Recommended Approach

Since you're using `docker-compose.dev.yml`, use the dev project name:

```bash
# Clean up
docker-compose -f docker-compose.dev.yml -p bot-prod down --remove-orphans
docker ps -a --filter "name=bot-prod" -q | xargs docker rm -f 2>/dev/null || true

# Start with correct project name
docker-compose -f docker-compose.dev.yml -p bot-dev up -d
```

This matches the container names in your compose file (`bot-dev-postgres`, `bot-dev-redis`, etc.)

---

## Build failure: "failed to solve: image ... already exists"

When the backend build fails at **exporting to image** with `ERROR: failed to build: failed to solve: image "docker.io/library/bot-dev_backend:latest": already exists`, the export layer is conflicting with an existing image.

**Fix:** Remove the image and rebuild with no cache:

```bash
# Dev
docker image rm bot-dev_backend:latest 2>/dev/null || true
docker compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend
docker compose -f docker-compose.dev.yml -p bot-dev up -d backend
```

Or use the script (from repo root):

- **Windows (PowerShell):** `.\scripts\dev-rebuild-backend.ps1`
- **Linux/macOS:** `./scripts/dev-rebuild-backend.sh`

---

## Worker 404 on POST /api/v1/agent/workers/events

If the worker logs `HTTP/1.1 404 Not Found` for `POST http://backend:8000/api/v1/agent/workers/events`, the backend container is usually running an **old image** that was built before that route existed or before a clean export.

**Fix:** Do a clean backend rebuild (see above). After rebuild, the route is registered and the worker can publish events.
