#!/bin/bash
# Clean and restart both environments - fixes ContainerConfig errors

set -e

echo "=========================================="
echo "Clean and Restart Both Environments"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Step 1: Stop everything
echo -e "${YELLOW}Step 1: Stopping all containers...${NC}"
docker-compose -f docker-compose.production.yml down --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

echo -e "${GREEN}✓ All containers stopped${NC}"
echo ""

# Step 2: Remove ALL bot containers (including corrupted ones)
echo -e "${YELLOW}Step 2: Removing all bot containers...${NC}"

# List and remove all bot containers
echo "Finding all bot containers..."
docker ps -a --filter "name=bot" --format "{{.Names}}" | while read container; do
    if [ ! -z "$container" ]; then
        echo "  Removing: $container"
        docker rm -f "$container" 2>/dev/null || true
    fi
done

# Force remove specific problematic containers
docker rm -f bot_postgres_1 bot_redis_1 bot_backend_1 bot_worker_1 bot_frontend_1 2>/dev/null || true
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true

# Remove any container with ContainerConfig error
docker ps -a | grep -E "bot|postgres|redis|backend|worker|frontend" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo -e "${GREEN}✓ All containers removed${NC}"
echo ""

# Step 3: Clean up networks (optional - will be recreated)
echo -e "${YELLOW}Step 3: Cleaning up networks...${NC}"
docker network rm bot_app-dev-network 2>/dev/null || echo "Dev network doesn't exist (OK)"
# Don't remove production network as it's external
echo -e "${GREEN}✓ Networks cleaned${NC}"
echo ""

# Step 4: Start Production
echo -e "${BLUE}=========================================="
echo "Starting PRODUCTION"
echo "==========================================${NC}"
echo ""

docker-compose -f docker-compose.production.yml up -d --remove-orphans postgres redis
sleep 5
docker-compose -f docker-compose.production.yml up -d --remove-orphans backend
sleep 10
docker-compose -f docker-compose.production.yml up -d --remove-orphans worker frontend proxy

echo ""
echo -e "${YELLOW}Production status:${NC}"
docker-compose -f docker-compose.production.yml ps

echo ""

# Step 5: Start Dev
echo -e "${BLUE}=========================================="
echo "Starting DEV"
echo "==========================================${NC}"
echo ""

docker-compose -f docker-compose.dev.yml up -d --remove-orphans postgres redis
sleep 5

# Create dev database
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai_dev;" 2>&1 | grep -v "already exists" || true

docker-compose -f docker-compose.dev.yml up -d --remove-orphans backend
sleep 15

# Run dev migrations
echo "Running dev migrations..."
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_runbook_environment.sql 2>&1 | grep -v "already exists" || true
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/add_deployment_approvals_table.sql 2>&1 | grep -v "already exists" || true

docker-compose -f docker-compose.dev.yml up -d --remove-orphans worker frontend

echo ""
echo -e "${YELLOW}Dev status:${NC}"
docker-compose -f docker-compose.dev.yml ps

echo ""

# Step 6: Final verification
echo -e "${BLUE}=========================================="
echo "Final Verification"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}All containers:${NC}"
docker ps --filter "name=bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo -e "${GREEN}=========================================="
echo "Complete!"
echo "==========================================${NC}"
echo ""
echo "Production containers should use default names (bot_backend_1, etc.)"
echo "Dev containers should use explicit names (bot-dev-backend, etc.)"
echo ""

