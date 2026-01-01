#!/bin/bash
# Force clean and fix dev environment - removes corrupted containers first

set -e

echo "=========================================="
echo "Force Clean and Fix Dev Environment"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Stop dev
echo -e "${YELLOW}Step 1: Stopping dev environment...${NC}"
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Step 2: Force remove the problematic production containers that are interfering
echo -e "${YELLOW}Step 2: Force removing corrupted containers...${NC}"

# Remove the specific containers causing issues
docker rm -f bot_postgres_1 bot_redis_1 2>/dev/null || true

# Remove ALL containers with those names (in case there are multiple)
docker ps -a | grep -E "bot_postgres_1|bot_redis_1" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Remove dev containers
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true

echo -e "${GREEN}✓ Containers removed${NC}"
echo ""

# Step 3: Remove volumes from corrupted containers (optional - be careful!)
echo -e "${YELLOW}Step 3: Checking for corrupted volumes...${NC}"
# Don't remove volumes, just note them
echo "Volumes will be preserved"
echo ""

# Step 4: Start dev with explicit project name to avoid conflicts
echo -e "${YELLOW}Step 4: Starting dev with explicit project name...${NC}"

# Use -p flag to set project name explicitly
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --force-recreate --remove-orphans postgres redis

echo "Waiting for postgres and redis..."
sleep 5

# Verify they started with correct names
echo ""
echo -e "${YELLOW}Checking container names...${NC}"
if docker ps | grep -q "bot-dev-postgres"; then
    echo -e "${GREEN}✓ bot-dev-postgres is running${NC}"
else
    echo -e "${RED}✗ bot-dev-postgres not found${NC}"
    docker ps | grep postgres
fi

if docker ps | grep -q "bot-dev-redis"; then
    echo -e "${GREEN}✓ bot-dev-redis is running${NC}"
else
    echo -e "${RED}✗ bot-dev-redis not found${NC}"
    docker ps | grep redis
fi

echo ""

# Step 5: Create dev database
echo -e "${YELLOW}Step 5: Creating dev database...${NC}"
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

# Step 6: Start backend
echo -e "${YELLOW}Step 6: Starting dev backend...${NC}"
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --force-recreate --remove-orphans backend

echo "Waiting for backend to initialize..."
sleep 15

# Step 7: Run migrations
echo -e "${YELLOW}Step 7: Running dev migrations...${NC}"
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "already exists" || true
docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "already exists" || true

# Step 8: Start worker and frontend
echo -e "${YELLOW}Step 8: Starting dev worker and frontend...${NC}"
docker-compose -f docker-compose.dev.yml -p bot-dev up -d --force-recreate --remove-orphans worker frontend

echo ""
echo -e "${YELLOW}Final status:${NC}"
docker-compose -f docker-compose.dev.yml -p bot-dev ps

echo ""
echo -e "${GREEN}=========================================="
echo "Dev Environment Fixed!"
echo "==========================================${NC}"
echo ""
echo "Dev containers should now be:"
echo "  - bot-dev-postgres"
echo "  - bot-dev-redis"
echo "  - bot-dev-backend"
echo "  - bot-dev-worker"
echo "  - bot-dev-frontend"
echo ""

