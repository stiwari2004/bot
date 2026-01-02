# Setup Dev Database and Tables

## Step 1: Verify Database Exists

```bash
# Check if dev database exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -c "\l" | grep troubleshooting_ai_dev
```

## Step 2: Check What Tables Exist

```bash
# List all tables in dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\dt"
```

## Step 3: Check if runbooks table exists and has environment column

```bash
# Check runbooks table structure
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"
```

## Step 4: Run Migrations (if tables exist but columns are missing)

```bash
# Migration 1: Add environment columns to runbooks
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql

# Migration 2: Create deployment_approvals table
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql
```

## Step 5: Verify Migrations Applied

```bash
# Check runbooks table has environment column
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" | grep -E "environment|promoted_from"

# Check deployment_approvals table exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals"
```

