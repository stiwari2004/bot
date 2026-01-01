# Deploy Dev Environment - Step by Step Guide

This guide walks you through setting up the dev environment with database migrations.

## Prerequisites

- Docker and Docker Compose installed
- Access to the production server
- Nginx configured for `dev.resolvify.tech` (already done)

## Step 1: Create Dev Database

The dev database will be created automatically when you start the dev containers, but you can also create it manually:

### Option A: Using Docker Compose (Recommended)

```bash
# Start the dev postgres container
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait a few seconds for postgres to be ready
sleep 5

# Create the database (if it doesn't exist)
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;"
```

### Option B: Manual SQL Command

If you need to connect directly to postgres:

```bash
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres
```

Then in psql:
```sql
CREATE DATABASE troubleshooting_ai_dev;
\q
```

## Step 2: Run Migrations on Dev Database

Apply the migrations to add environment tracking and deployment approvals:

```bash
# Migration 1: Add environment columns to runbooks
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql

# Migration 2: Create deployment_approvals table
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

**Or use the automated script:**
```bash
chmod +x scripts/setup-dev-environment.sh
./scripts/setup-dev-environment.sh
```

## Step 3: Run Migrations on Production Database

Apply the same migrations to production (important for runbook promotion to work):

```bash
# Migration 1: Add environment columns to runbooks
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_runbook_environment.sql

# Migration 2: Create deployment_approvals table
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_deployment_approvals_table.sql
```

## Step 4: Verify Migrations

Check that migrations were applied correctly:

### Dev Database:
```bash
# Check runbooks table has environment column
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" | grep environment

# Check deployment_approvals table exists
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals"
```

### Production Database:
```bash
# Check runbooks table has environment column
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai -c "\d runbooks" | grep environment

# Check deployment_approvals table exists
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai -c "\d deployment_approvals"
```

## Step 5: Configure Environment Variables

Ensure your `backend/.env` file has:

```bash
# For dev environment
ENVIRONMENT=development
DEBUG=true

# Database URL for dev (docker-compose.dev.yml will override this)
DATABASE_URL=postgresql://postgres:dev_password_change_me@postgres:5432/troubleshooting_ai_dev

# Add dev.resolvify.tech to allowed hosts
ALLOWED_HOSTS=["https://dev.resolvify.tech","https://resolvify.tech","https://admin.resolvify.tech","https://demo.resolvify.tech"]
```

## Step 6: Start Dev Environment

```bash
# Build and start all dev services
docker-compose -f docker-compose.dev.yml up -d --build

# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

## Step 7: Verify Dev Environment is Running

1. **Check containers are running:**
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```
   All services should show "Up"

2. **Check backend health:**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Check frontend:**
   ```bash
   curl http://localhost:3005
   ```

4. **Access via domain:**
   - Open browser: `https://dev.resolvify.tech`
   - Should see the application

## Step 8: Test Runbook Creation in Dev

1. Log in to `https://dev.resolvify.tech`
2. Create a test runbook
3. Verify it's created with `environment='dev'`:
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, title, environment FROM runbooks ORDER BY id DESC LIMIT 5;"
   ```

## Troubleshooting

### Database connection errors:
```bash
# Check postgres is running
docker-compose -f docker-compose.dev.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.dev.yml logs postgres

# Test connection
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT 1;"
```

### Migration errors:
```bash
# Check if columns already exist
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"

# If migrations fail, you can run them manually
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev
# Then paste the SQL from the migration files
```

### Nginx not routing correctly:
```bash
# Check nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Port conflicts:
- Dev backend: port 8001 (should not conflict with production on 8000)
- Dev frontend: port 3005 (should not conflict with production on 3000)
- Dev postgres: internal only (no host port exposed)

## Quick Reference Commands

```bash
# Start dev environment
docker-compose -f docker-compose.dev.yml up -d

# Stop dev environment
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend

# Rebuild after code changes
docker-compose -f docker-compose.dev.yml up -d --build

# Access dev database
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev

# Check runbooks in dev
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, title, environment, status FROM runbooks ORDER BY id DESC LIMIT 10;"
```

## Next Steps

Once dev environment is running:

1. Test runbook creation in dev
2. Test runbook promotion workflow
3. Set up GitHub Actions secrets for CI/CD
4. Configure deployment approvals

