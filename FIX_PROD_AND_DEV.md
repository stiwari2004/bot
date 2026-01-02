# Fix Production and Dev Isolation Issues

## Issue 1: Production 500 Error - Check Backend Logs

```bash
# Check production backend logs for the actual error
docker-compose -f docker-compose.production.yml logs backend | tail -50 | grep -i "error\|exception\|traceback\|deployment_approval\|metadata"
```

## Issue 2: Dev ContainerConfig Error - Clean Corrupted Container

```bash
# Remove the corrupted dev backend container completely
docker rm -f bot-dev-backend 2>/dev/null || true

# Remove any orphaned containers
docker ps -a | grep bot-dev-backend | awk '{print $1}' | xargs -r docker rm -f

# Remove the corrupted image if it exists
docker rmi bot_backend:latest 2>/dev/null || true
docker images | grep bot.*backend | awk '{print $3}' | xargs -r docker rmi 2>/dev/null || true

# Now rebuild and start fresh
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend
```

## Issue 3: Verify Production and Dev Are Isolated

```bash
# Check production containers
docker-compose -f docker-compose.production.yml ps

# Check dev containers  
docker-compose -f docker-compose.dev.yml -p bot-dev ps

# Check networks (should be different)
docker network ls | grep bot

# Check volumes (should be different)
docker volume ls | grep bot
```

## Issue 4: Fix Production - Rebuild if Model Fix Not Applied

```bash
# Check if production backend has the fix
docker-compose -f docker-compose.production.yml exec backend grep -A 2 "approval_metadata" /app/app/models/deployment_approval.py || echo "Fix not found"

# If fix not found, rebuild production backend
docker-compose -f docker-compose.production.yml stop backend
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.production.yml build backend
docker-compose -f docker-compose.production.yml up -d backend
```

