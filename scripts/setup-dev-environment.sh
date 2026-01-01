#!/bin/bash
# Setup Dev Environment - Complete Guide
# This script helps set up the dev database and run migrations

set -e

echo "=========================================="
echo "Dev Environment Setup Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Create Dev Database
echo -e "${YELLOW}Step 1: Creating dev database...${NC}"
echo ""

# Check if using Docker Compose
if docker-compose -f docker-compose.dev.yml ps postgres 2>/dev/null | grep -q "Up"; then
    echo "PostgreSQL container is running via docker-compose"
    echo "Creating database troubleshooting_ai_dev..."
    
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" || echo "Database may already exist (this is OK)"
    
    echo -e "${GREEN}✓ Dev database created${NC}"
else
    echo "PostgreSQL container not running. Starting it..."
    docker-compose -f docker-compose.dev.yml up -d postgres
    
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    echo "Creating database troubleshooting_ai_dev..."
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" || echo "Database may already exist (this is OK)"
    
    echo -e "${GREEN}✓ Dev database created${NC}"
fi

echo ""

# Step 2: Run migrations on Dev Database
echo -e "${YELLOW}Step 2: Running migrations on dev database...${NC}"
echo ""

echo "Applying runbook environment migration..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -f /docker-entrypoint-initdb.d/add_runbook_environment.sql 2>/dev/null || \
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql

echo "Applying deployment approvals table migration..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -f /docker-entrypoint-initdb.d/add_deployment_approvals_table.sql 2>/dev/null || \
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql

echo -e "${GREEN}✓ Dev database migrations applied${NC}"
echo ""

# Step 3: Run migrations on Production Database
echo -e "${YELLOW}Step 3: Running migrations on production database...${NC}"
echo ""

if docker-compose -f docker-compose.production.yml ps postgres 2>/dev/null | grep -q "Up"; then
    echo "Production PostgreSQL container is running"
    echo "Applying runbook environment migration to production..."
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_runbook_environment.sql || \
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -f /docker-entrypoint-initdb.d/add_runbook_environment.sql
    
    echo "Applying deployment approvals table migration to production..."
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_deployment_approvals_table.sql || \
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -f /docker-entrypoint-initdb.d/add_deployment_approvals_table.sql
    
    echo -e "${GREEN}✓ Production database migrations applied${NC}"
else
    echo -e "${YELLOW}⚠ Production database not running. You can run migrations manually later:${NC}"
    echo "  docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_runbook_environment.sql"
    echo "  docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_deployment_approvals_table.sql"
fi

echo ""

# Step 4: Verify migrations
echo -e "${YELLOW}Step 4: Verifying migrations...${NC}"
echo ""

echo "Checking dev database schema..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" | grep -q "environment" && echo -e "${GREEN}✓ environment column exists${NC}" || echo -e "${RED}✗ environment column missing${NC}"
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals" > /dev/null 2>&1 && echo -e "${GREEN}✓ deployment_approvals table exists${NC}" || echo -e "${RED}✗ deployment_approvals table missing${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start dev environment: docker-compose -f docker-compose.dev.yml up -d"
echo "2. Check logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "3. Access dev environment at: https://dev.resolvify.tech"
echo ""

