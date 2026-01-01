# Manual Dev Environment Setup - Step by Step Commands

**Production is already running - DO NOT touch it. These commands are for DEV ONLY.**

## Step 1: Stop Dev (if running)

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev down --remove-orphans
```

## Step 2: Remove Any Conflicting Containers

```bash
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true
docker rm -f bot_postgres_1 bot_redis_1 2>/dev/null || true
```

## Step 3: Start Dev Postgres and Redis

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev up -d postgres redis
```

Wait 5 seconds, then verify:
```bash
docker ps | grep bot-dev
```

You should see:
- `bot-dev-postgres`
- `bot-dev-redis`

## Step 4: Create Dev Database

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;"
```

## Step 5: Create Tables Manually (Copy Schema from Production)

```bash
# Dump production schema (structure only, no data)
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U postgres -d troubleshooting_ai --schema-only > /tmp/prod_schema.sql

# Apply to dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < /tmp/prod_schema.sql
```

**OR** if that doesn't work, start backend to create tables, then stop it:

```bash
# Start backend (it will create tables)
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend

# Wait 30 seconds for tables to be created
sleep 30

# Verify tables exist
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"
```

## Step 6: Run Migrations (ONLY after tables exist)

```bash
# Check if runbooks table exists first
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"

# If table exists, run migrations:
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql

docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

## Step 7: Start Dev Backend (if not already running)

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend
```

## Step 8: Start Dev Worker and Frontend

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev up -d worker frontend
```

## Step 9: Verify Everything

```bash
# Check all dev containers
docker-compose -f docker-compose.dev.yml -p bot-dev ps

# Check container names (should all start with bot-dev-)
docker ps | grep bot-dev

# Test backend
curl http://localhost:8001/health

# Test frontend
curl http://localhost:3005
```

## Important: Always Use `-p bot-dev`

**Every docker-compose command for dev MUST include `-p bot-dev`:**

```bash
# Start
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# Stop
docker-compose -f docker-compose.dev.yml -p bot-dev down

# Logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs -f

# Exec
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend bash
```

## Troubleshooting

### If tables don't exist:
```bash
# Check backend logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -50

# Check if backend is running
docker-compose -f docker-compose.dev.yml -p bot-dev ps backend
```

### If worker is unhealthy:
```bash
# Check worker logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs worker

# Restart worker
docker-compose -f docker-compose.dev.yml -p bot-dev restart worker
```

### If frontend build fails:
```bash
# Rebuild frontend
docker-compose -f docker-compose.dev.yml -p bot-dev build frontend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d frontend
```

