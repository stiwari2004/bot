# Fix: Dev Docker Compose Using Production Containers

## The Problem

Docker Compose is trying to recreate production containers (`bot_postgres_1`, `bot_redis_1`) when starting dev because both compose files use the same default project name (directory name).

## The Solution

Use the `-p` flag to specify a different project name for dev:

```bash
# Always use -p bot-dev when running dev compose
docker-compose -f docker-compose.dev.yml -p bot-dev up -d
```

## Quick Fix Commands

```bash
# 1. Stop dev (if running)
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans

# 2. Remove corrupted containers
docker rm -f bot_postgres_1 bot_redis_1 2>/dev/null || true

# 3. Start dev with explicit project name
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans postgres redis
sleep 5

# 4. Create dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

# 5. Start backend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans backend
sleep 15

# 6. Run migrations
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql

# 7. Start worker and frontend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --remove-orphans worker frontend

# 8. Verify
docker-compose -f docker-compose.dev.yml -p bot-dev ps
```

## Why This Works

- `-p bot-dev` sets the project name to "bot-dev" instead of default "bot"
- This prevents docker-compose from trying to manage production containers
- Dev containers will be named: `bot-dev-postgres`, `bot-dev-redis`, etc.
- Production containers remain: `bot_postgres_1`, `bot_redis_1`, etc.

## Always Use -p Flag for Dev

**Every time you run docker-compose for dev, use `-p bot-dev`:**

```bash
# Start
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# Stop
docker-compose -f docker-compose.dev.yml -p bot-dev down

# Logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs -f

# Restart
docker-compose -f docker-compose.dev.yml -p bot-dev restart

# Exec
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend bash
```

## Production (No Changes Needed)

Production continues to work normally:
```bash
docker-compose -f docker-compose.production.yml up -d
```

