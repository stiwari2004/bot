# Fix Dev Database Tables

The schema dump didn't work. Here are commands to fix it:

## Option 1: Wait for Backend to Create Tables (Recommended)

The backend creates tables automatically when it starts. Check if it's doing that:

```bash
# Check backend logs to see if it's creating tables
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | grep -i "table\|create\|alembic\|migration" | tail -20

# Check if backend is healthy
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend curl http://localhost:8000/health

# Wait a bit longer and check again
sleep 30
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\dt"
```

If tables still don't exist, the backend might not be creating them. Check the full backend logs:

```bash
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -50
```

## Option 2: Copy Tables from Production (If Backend Won't Create Them)

```bash
# List all tables in production
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai -c "\dt"

# Get the CREATE TABLE statements from production
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U postgres -d troubleshooting_ai --schema-only --no-owner --no-privileges > /tmp/prod_schema_clean.sql

# Apply to dev (this should work better)
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < /tmp/prod_schema_clean.sql

# Verify tables were created
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\dt"
```

## Option 3: Check What's Actually in Dev Database

```bash
# List all tables in dev
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\dt"

# List all schemas
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\dn"

# Check if tables are in a different schema
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_schema, table_name;"
```

## Once Tables Exist, Run Migrations

```bash
# Verify runbooks table exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"

# If it exists, run migrations
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

