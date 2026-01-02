# Fix Production ContainerConfig Error

## Step 1: Remove Corrupted Production Backend Container

```bash
# Stop and remove the corrupted backend container
docker-compose -f docker-compose.production.yml stop backend
docker rm -f bot_backend_1 2>/dev/null || true

# Remove any orphaned backend containers
docker ps -a | grep bot.*backend | grep -v bot-dev | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# List all containers to see what's there
docker ps -a | grep bot
```

## Step 2: Clean Up Corrupted Images (Optional but Recommended)

```bash
# Remove the backend image to force a fresh build
docker rmi bot_backend:latest 2>/dev/null || true

# Clean up dangling images
docker image prune -f
```

## Step 3: Rebuild and Start Production Backend

```bash
# Rebuild without BuildKit (to avoid permission issues)
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.production.yml build backend

# Start the backend
docker-compose -f docker-compose.production.yml up -d backend

# Wait and check status
sleep 10
docker-compose -f docker-compose.production.yml ps backend
docker-compose -f docker-compose.production.yml logs backend | tail -30
```

## Step 4: Verify Backend is Working

```bash
# Test health endpoint
curl http://localhost:8000/health

# Check for errors in logs
docker-compose -f docker-compose.production.yml logs backend | grep -i "error\|exception" | tail -10
```

