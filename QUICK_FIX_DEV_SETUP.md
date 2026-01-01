# Quick Fix for Dev Environment Setup

## Problem
1. `ContainerConfig` error when starting dev postgres
2. `runbooks` table doesn't exist (fresh database)

## Solution

### Step 1: Clean up Docker and start fresh

```bash
# Stop and remove all dev containers
docker-compose -f docker-compose.dev.yml down --remove-orphans

# Remove the problematic container specifically
docker rm -f 659d7f6ed878_bot_postgres_1 2>/dev/null || true

# Remove any orphaned postgres containers
docker ps -a | grep "bot.*postgres" | awk '{print $1}' | xargs -r docker rm -f

# Clean up dangling images
docker image prune -f
```

### Step 2: Start postgres fresh

```bash
# Start postgres (will create database automatically)
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait for it to be ready
sleep 5

# Verify it's running
docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U postgres
```

### Step 3: Create database (if needed)

```bash
# Create the dev database
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;"
```

### Step 4: Initialize tables (start backend to create schema)

The tables are created by SQLAlchemy when the backend starts. Start the backend briefly:

```bash
# Start backend (it will create all tables on startup)
docker-compose -f docker-compose.dev.yml up -d backend

# Wait for backend to initialize schema
sleep 15

# Check if tables were created
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"
```

If tables still don't exist, check backend logs:
```bash
docker-compose -f docker-compose.dev.yml logs backend | tail -50
```

### Step 5: Run migrations

Once tables exist, run the migrations:

```bash
# Migration 1: Add environment columns
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql

# Migration 2: Create deployment_approvals table
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

### Step 6: Verify

```bash
# Check environment column exists
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" | grep environment

# Check deployment_approvals table exists
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals"
```

### Step 7: Start all services

```bash
# Start all dev services
docker-compose -f docker-compose.dev.yml up -d

# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

## Automated Script

Or use the automated script:

```bash
chmod +x scripts/fix-dev-docker-and-setup.sh
./scripts/fix-dev-docker-and-setup.sh
```

## Alternative: Copy schema from production

If you want to copy the schema from production:

```bash
# Dump schema from production (structure only, no data)
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U postgres -d troubleshooting_ai --schema-only > /tmp/prod_schema.sql

# Apply to dev
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < /tmp/prod_schema.sql

# Then run migrations
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

