# Debug Worker Container Unhealthy Issue

## Problem
Worker container is failing to start because container "5af5db31db90" is unhealthy.

## Diagnosis Steps

Run these commands to diagnose:

```bash
# 1. Check which container is actually unhealthy
docker ps -a --filter "id=5af5db31db90" --format "{{.Names}}\t{{.Status}}"

# 2. Check backend container health
docker ps -a --filter "name=bot-dev-backend" --format "{{.Names}}\t{{.Status}}"

# 3. Check backend logs
docker logs bot-dev-backend --tail 50

# 4. Check worker logs (if it started)
docker logs bot-dev-worker --tail 50

# 5. Check backend health endpoint
docker exec bot-dev-backend curl -f http://localhost:8000/health || echo "Health check failed"

# 6. Check all container statuses
docker-compose -f docker-compose.dev.yml -p bot-dev ps
```

## Common Causes

1. **Backend not passing health check** - The backend healthcheck might be failing
2. **Backend taking too long to start** - Health check might timeout before backend is ready
3. **Database connection issues** - Backend can't connect to postgres
4. **Port conflicts** - Backend port might be in use

## Quick Fixes

### Option 1: Increase health check timeout
If backend is slow to start, temporarily remove the health check dependency:

```bash
# Edit docker-compose.dev.yml, change worker depends_on from:
depends_on:
  backend:
    condition: service_healthy
# To:
depends_on:
  backend:
    condition: service_started
```

### Option 2: Restart backend and wait
```bash
# Stop everything
docker-compose -f docker-compose.dev.yml -p bot-dev down

# Start backend first and wait for it to be healthy
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend
sleep 30  # Wait for backend to become healthy

# Then start worker
docker-compose -f docker-compose.dev.yml -p bot-dev up -d worker
```

### Option 3: Check backend health check configuration
The backend healthcheck in docker-compose.dev.yml should be:
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

Make sure `curl` is installed in the backend image or change to use Python/other tool.
