# Fix Backend 404 Errors - Rebuild Backend Container

## Problem
1. Backend endpoints returning 404: `/api/v1/tickets/demo/tickets`, `/api/v1/alerts/alerts`, `/api/v1/change-tickets`, `/api/v1/agent/pending-approvals`
2. Docker Compose error: `ContainerConfig` KeyError due to corrupted container referencing deleted image

## Root Cause
- Backend container is running old code without router registration logging
- Corrupted container `0c3cae750d41_bot-prod-backend` references deleted image
- Routers may not be registered due to import failures

## Solution

### Option 1: Use the automated script (Recommended)

```bash
chmod +x fix_backend_rebuild.sh
./fix_backend_rebuild.sh
```

### Option 2: Manual steps

```bash
# 1. Stop backend service
docker-compose -f docker-compose.production.yml -p bot-prod stop backend

# 2. Remove corrupted container
docker rm -f 0c3cae750d41 2>/dev/null || true
docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}" | xargs -r docker rm -f

# 3. Clean up orphaned containers
docker-compose -f docker-compose.production.yml -p bot-prod down --remove-orphans

# 4. Rebuild backend image (with new code)
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend

# 5. Start backend
docker-compose -f docker-compose.production.yml -p bot-prod up -d backend

# 6. Wait for startup and check logs
sleep 5
docker logs bot-prod-backend --tail 100 | grep -i "router\|import\|registered"
```

### Option 3: One-liner

```bash
docker-compose -f docker-compose.production.yml -p bot-prod stop backend && \
docker rm -f 0c3cae750d41 2>/dev/null || true && \
docker ps -a --filter "name=bot-prod-backend" --format "{{.ID}}" | xargs -r docker rm -f && \
docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend && \
docker-compose -f docker-compose.production.yml -p bot-prod up -d backend
```

## Verification

After rebuilding, check for router registration messages:

```bash
docker logs bot-prod-backend --tail 100 | grep -i "router\|import\|registered"
```

You should see:
- `"Successfully imported Phase 2 endpoints"`
- `"Registered ticket_ingestion router"`
- `"Registered agent_execution router"`
- `"Registered alerts router"`
- `"Registered change_tickets router"`

## Test Endpoints

```bash
# Test tickets endpoint (should return 401/403, not 404)
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/tickets/demo/tickets

# Test alerts endpoint
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/alerts/alerts

# Test change-tickets endpoint
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/change-tickets

# Test agent pending-approvals endpoint
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/agent/pending-approvals
```

**Note:** These endpoints require authentication, so 401/403 is expected. 404 means the route doesn't exist.

## If Still Getting 404s

Run the diagnostic script:

```bash
chmod +x verify_backend_code.sh
./verify_backend_code.sh
```

This will check:
1. If the router logging code exists in the container
2. If modules can be imported
3. If routers have the `router` attribute
