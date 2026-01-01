# Setup Both Production and Dev Environments

This guide ensures both production and dev environments can run simultaneously without conflicts.

## Quick Setup (Automated)

```bash
chmod +x scripts/setup-both-environments.sh
./scripts/setup-both-environments.sh
```

## Manual Setup Steps

### Step 1: Stop Everything

```bash
# Stop both environments
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.dev.yml down
```

### Step 2: Clean Up Conflicting Containers

```bash
# Remove any containers with conflicting names
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true

# Remove orphaned containers
docker ps -a | grep "bot.*postgres" | grep -v "bot-dev-postgres" | awk '{print $1}' | xargs -r docker rm -f
```

### Step 3: Ensure Networks Exist

```bash
# Production network (external)
docker network create bot_app-network 2>/dev/null || echo "Network exists (OK)"

# Dev network will be created automatically
```

### Step 4: Start Production

```bash
# Start production services in order
docker-compose -f docker-compose.production.yml up -d postgres redis
sleep 5
docker-compose -f docker-compose.production.yml up -d backend
sleep 10
docker-compose -f docker-compose.production.yml up -d worker frontend proxy

# Verify
docker-compose -f docker-compose.production.yml ps
```

### Step 5: Run Production Migrations

```bash
# Migration 1: Add environment tracking
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_runbook_environment.sql

# Migration 2: Create deployment_approvals table
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_deployment_approvals_table.sql
```

### Step 6: Start Dev

```bash
# Start dev services in order
docker-compose -f docker-compose.dev.yml up -d postgres redis
sleep 5

# Create dev database
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

# Start backend to create tables
docker-compose -f docker-compose.dev.yml up -d backend
sleep 15

# Run dev migrations
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql

# Start worker and frontend
docker-compose -f docker-compose.dev.yml up -d worker frontend

# Verify
docker-compose -f docker-compose.dev.yml ps
```

## Container Names

### Production Containers
- Uses default Docker Compose naming: `bot_backend_1`, `bot_frontend_1`, etc.
- Network: `bot_app-network` (external)
- Ports: 8000 (backend), 3004 (frontend), 8443 (proxy HTTPS)

### Dev Containers
- Uses explicit names: `bot-dev-backend`, `bot-dev-frontend`, etc.
- Network: `bot_app-dev-network` (internal)
- Ports: 8001 (backend), 3005 (frontend)

## Verification

### Check Both Environments

```bash
# Production
docker-compose -f docker-compose.production.yml ps

# Dev
docker-compose -f docker-compose.dev.yml ps

# All containers
docker ps --filter "name=bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Test Endpoints

```bash
# Production backend
curl http://localhost:8000/health

# Dev backend
curl http://localhost:8001/health

# Production frontend
curl http://localhost:3004

# Dev frontend
curl http://localhost:3005
```

## Troubleshooting

### If Production Won't Start

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Check network
docker network ls | grep bot_app-network

# Restart production
docker-compose -f docker-compose.production.yml restart
```

### If Dev Won't Start

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs

# Check if dev database exists
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -l | grep troubleshooting_ai_dev

# Restart dev
docker-compose -f docker-compose.dev.yml restart
```

### If Containers Conflict

```bash
# List all bot containers
docker ps -a | grep bot

# Remove specific conflicting container
docker rm -f <container_name>

# Restart the affected environment
docker-compose -f docker-compose.production.yml up -d
# or
docker-compose -f docker-compose.dev.yml up -d
```

## Port Summary

| Service | Production | Dev |
|---------|-----------|-----|
| Backend | 8000 | 8001 |
| Frontend | 3004 | 3005 |
| Proxy HTTPS | 8443 | N/A (nginx on host) |
| Postgres | Internal | Internal |
| Redis | Internal | Internal |

## Network Isolation

- **Production**: Uses external network `bot_app-network`
- **Dev**: Uses internal network `bot_app-dev-network`
- They are completely isolated and won't interfere with each other

