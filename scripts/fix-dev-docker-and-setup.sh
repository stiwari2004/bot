#!/bin/bash
# Fix Docker ContainerConfig error and setup dev environment

set -e

echo "=========================================="
echo "Fixing Docker Issues and Setting Up Dev Environment"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Clean up corrupted containers
echo -e "${YELLOW}Step 1: Cleaning up corrupted Docker containers...${NC}"

# Stop and remove any existing dev containers
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Remove the specific problematic container if it exists
docker rm -f 659d7f6ed878_bot_postgres_1 2>/dev/null || true

# Find and remove any orphaned postgres containers for dev
docker ps -a | grep "bot.*postgres" | grep -v "bot_postgres_1" | awk '{print $1}' | xargs -r docker rm -f

# Clean up any dangling images
docker image prune -f

echo -e "${GREEN}✓ Docker cleanup complete${NC}"
echo ""

# Step 2: Start fresh postgres container
echo -e "${YELLOW}Step 2: Starting fresh postgres container...${NC}"

# Start postgres (this will create the database automatically via init.sql)
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Verify postgres is running
if ! docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
    docker-compose -f docker-compose.dev.yml logs postgres
    exit 1
fi

echo ""

# Step 3: Verify database was created and initialized
echo -e "${YELLOW}Step 3: Verifying database initialization...${NC}"

# Check if database exists
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -lqt | cut -d \| -f 1 | grep -qw troubleshooting_ai_dev; then
    echo -e "${GREEN}✓ Database troubleshooting_ai_dev exists${NC}"
else
    echo "Creating database troubleshooting_ai_dev..."
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;"
    
    # Run init.sql to create all base tables
    echo "Running init.sql to create base tables..."
    if [ -f "backend/sql/init.sql" ]; then
        docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/init.sql
    else
        echo -e "${YELLOW}⚠ init.sql not found, tables may need to be created manually${NC}"
    fi
fi

# Check if runbooks table exists
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ runbooks table exists${NC}"
else
    echo -e "${YELLOW}⚠ runbooks table doesn't exist yet.${NC}"
    echo "  Tables are created by SQLAlchemy when the backend starts."
    echo "  We'll start the backend briefly to initialize the schema..."
    
    # Start backend to create tables (it will create them on startup)
    echo "Starting backend to initialize database schema..."
    docker-compose -f docker-compose.dev.yml up -d backend
    
    # Wait for backend to initialize
    echo "Waiting for backend to initialize schema..."
    sleep 10
    
    # Check again
    if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ runbooks table created${NC}"
    else
        echo -e "${YELLOW}⚠ Tables not created yet. Check backend logs:${NC}"
        echo "  docker-compose -f docker-compose.dev.yml logs backend"
        echo "  You may need to wait a bit longer or check for errors."
    fi
fi

echo ""

# Step 4: Run migrations
echo -e "${YELLOW}Step 4: Running migrations...${NC}"

echo "Applying runbook environment migration..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "already exists" || true

echo "Applying deployment approvals table migration..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "already exists" || true

echo -e "${GREEN}✓ Migrations applied${NC}"
echo ""

# Step 5: Verify migrations
echo -e "${YELLOW}Step 5: Verifying migrations...${NC}"

# Check environment column
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" 2>/dev/null | grep -q "environment"; then
    echo -e "${GREEN}✓ environment column exists in runbooks table${NC}"
else
    echo -e "${RED}✗ environment column missing${NC}"
fi

# Check deployment_approvals table
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ deployment_approvals table exists${NC}"
else
    echo -e "${RED}✗ deployment_approvals table missing${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start all dev services: docker-compose -f docker-compose.dev.yml up -d"
echo "2. Check status: docker-compose -f docker-compose.dev.yml ps"
echo "3. View logs: docker-compose -f docker-compose.dev.yml logs -f"
echo ""

