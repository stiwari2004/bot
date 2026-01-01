# Quick Start Dev Environment

## The Problem
- Docker Compose uses directory name as project name by default
- Both dev and production use "bot" as project name → conflicts
- Tables don't exist when migrations run

## The Solution

**ALWAYS use `-p bot-dev` flag for dev commands!**

## Quick Start Commands

```bash
# 1. Stop dev (if running)
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans

# 2. Remove corrupted containers
docker rm -f bot_postgres_1 bot_redis_1 2>/dev/null || true

# 3. Start dev postgres and redis
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans postgres redis
sleep 5

# 4. Create dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

# 5. Start backend (it will create tables)
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans backend

# 6. WAIT for backend to create tables (check every 5 seconds)
echo "Waiting for backend to create tables..."
for i in {1..12}; do
    sleep 5
    if docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
        echo "✓ Tables created!"
        break
    fi
    echo "  Waiting... ($i/12)"
done

# 7. Run migrations (ONLY after tables exist)
if docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
    echo "Running migrations..."
    docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "ERROR" || true
    docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "ERROR" || true
fi

# 8. Start worker and frontend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans worker frontend

# 9. Verify
docker-compose -f docker-compose.dev.yml -p bot-dev ps
```

## Important Notes

1. **ALWAYS use `-p bot-dev`** for dev commands
2. **Wait for tables** before running migrations
3. **Production is unaffected** - it uses default project name "bot"

## Container Names

**Dev (with `-p bot-dev`):**
- `bot-dev-postgres`
- `bot-dev-redis`
- `bot-dev-backend`
- `bot-dev-worker`
- `bot-dev-frontend`

**Production (default):**
- `bot_postgres_1`
- `bot_redis_1`
- `bot_backend_1`
- `bot_worker_1`
- `bot_frontend_1`

## Troubleshooting

If tables don't exist after 60 seconds:
```bash
# Check backend logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -50

# Check if backend is healthy
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend curl http://localhost:8000/health
```

