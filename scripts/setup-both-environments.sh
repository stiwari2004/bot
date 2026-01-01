#!/bin/bash
# Setup Both Production and Dev Environments
# Ensures both can run simultaneously without conflicts

set -e

echo "=========================================="
echo "Setting Up Both Production and Dev Environments"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Step 1: Stop everything first
echo -e "${YELLOW}Step 1: Stopping all containers...${NC}"
docker-compose -f docker-compose.production.yml down 2>/dev/null || true
docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

echo -e "${GREEN}✓ All containers stopped${NC}"
echo ""

# Step 2: Clean up any conflicting containers
echo -e "${YELLOW}Step 2: Cleaning up conflicting containers...${NC}"

# Remove any dev containers with wrong names
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true

# Remove any orphaned containers
docker ps -a | grep "bot.*postgres" | grep -v "bot-dev-postgres" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
docker ps -a | grep "bot.*redis" | grep -v "bot-dev-redis" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
docker ps -a | grep "bot.*backend" | grep -v "bot-dev-backend" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
docker ps -a | grep "bot.*worker" | grep -v "bot-dev-worker" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
docker ps -a | grep "bot.*frontend" | grep -v "bot-dev-frontend" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Step 3: Ensure networks exist
echo -e "${YELLOW}Step 3: Setting up Docker networks...${NC}"

# Production network (external)
if ! docker network ls | grep -q "bot_app-network"; then
    echo "Creating production network: bot_app-network"
    docker network create bot_app-network || echo "Network may already exist (this is OK)"
else
    echo -e "${GREEN}✓ Production network exists${NC}"
fi

# Dev network (will be created by docker-compose)
echo -e "${GREEN}✓ Networks ready${NC}"
echo ""

# Step 4: Start Production Environment
echo -e "${BLUE}=========================================="
echo "Setting Up PRODUCTION Environment"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}Starting production services...${NC}"

# Start production in order
docker-compose -f docker-compose.production.yml up -d postgres redis
echo "Waiting for production postgres and redis..."
sleep 5

docker-compose -f docker-compose.production.yml up -d backend
echo "Waiting for production backend..."
sleep 10

docker-compose -f docker-compose.production.yml up -d worker frontend proxy
echo "Waiting for production worker and frontend..."
sleep 5

# Verify production
echo ""
echo -e "${YELLOW}Verifying production services...${NC}"
if docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Production services started${NC}"
    docker-compose -f docker-compose.production.yml ps
else
    echo -e "${RED}✗ Production services failed to start${NC}"
    docker-compose -f docker-compose.production.yml logs --tail=20
    exit 1
fi

echo ""

# Step 5: Run Production Migrations
echo -e "${YELLOW}Running production database migrations...${NC}"

# Check if migrations are needed
if docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "\d runbooks" 2>/dev/null | grep -q "environment"; then
    echo -e "${GREEN}✓ Production runbooks table already has environment column${NC}"
else
    echo "Applying runbook environment migration to production..."
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "already exists" || true
fi

if docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "\d deployment_approvals" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Production deployment_approvals table exists${NC}"
else
    echo "Creating deployment_approvals table in production..."
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "already exists" || true
fi

echo ""

# Step 6: Start Dev Environment
echo -e "${BLUE}=========================================="
echo "Setting Up DEV Environment"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}Starting dev services...${NC}"

# Start dev in order
docker-compose -f docker-compose.dev.yml up -d postgres redis
echo "Waiting for dev postgres and redis..."
sleep 5

# Create dev database if it doesn't exist
echo "Ensuring dev database exists..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

# Start backend to create tables
docker-compose -f docker-compose.dev.yml up -d backend
echo "Waiting for dev backend to initialize schema..."
sleep 15

# Verify tables were created
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dev runbooks table exists${NC}"
else
    echo -e "${YELLOW}⚠ Dev runbooks table not created yet, waiting longer...${NC}"
    sleep 10
    if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dev runbooks table exists${NC}"
    else
        echo -e "${RED}✗ Dev runbooks table still missing. Check backend logs.${NC}"
        docker-compose -f docker-compose.dev.yml logs backend | tail -20
    fi
fi

# Run dev migrations
echo "Running dev database migrations..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "already exists" || true
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "already exists" || true

# Start dev worker and frontend
docker-compose -f docker-compose.dev.yml up -d worker frontend
echo "Waiting for dev worker and frontend..."
sleep 5

# Verify dev
echo ""
echo -e "${YELLOW}Verifying dev services...${NC}"
if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Dev services started${NC}"
    docker-compose -f docker-compose.dev.yml ps
else
    echo -e "${RED}✗ Dev services failed to start${NC}"
    docker-compose -f docker-compose.dev.yml logs --tail=20
fi

echo ""

# Step 7: Final Verification
echo -e "${BLUE}=========================================="
echo "Final Verification"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}Production Containers:${NC}"
docker-compose -f docker-compose.production.yml ps

echo ""
echo -e "${YELLOW}Dev Containers:${NC}"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo -e "${YELLOW}Container Name Summary:${NC}"
echo "Production:"
docker-compose -f docker-compose.production.yml ps --format json 2>/dev/null | grep -o '"Name":"[^"]*"' | sed 's/"Name":"/  - /' | sed 's/"$//' || docker ps --filter "name=bot_" --format "  - {{.Names}}" | grep -v "bot-dev"

echo ""
echo "Dev:"
docker ps --filter "name=bot-dev" --format "  - {{.Names}}"

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Production:"
echo "  - Backend: http://localhost:8000"
echo "  - Frontend: http://localhost:3004"
echo "  - Proxy: http://localhost:8443 (HTTPS)"
echo ""
echo "Dev:"
echo "  - Backend: http://localhost:8001"
echo "  - Frontend: http://localhost:3005"
echo "  - Access: https://dev.resolvify.tech"
echo ""
echo "Both environments are now running independently!"
echo ""

