#!/bin/bash
# Fix unhealthy worker container in dev environment

set -e

echo "=========================================="
echo "Fixing Unhealthy Worker Container"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Check worker status
echo -e "${YELLOW}Step 1: Checking worker container status...${NC}"
docker-compose -f docker-compose.dev.yml ps worker

echo ""

# Step 2: Check worker logs
echo -e "${YELLOW}Step 2: Checking worker logs...${NC}"
docker-compose -f docker-compose.dev.yml logs --tail=50 worker

echo ""

# Step 3: Stop and remove unhealthy worker
echo -e "${YELLOW}Step 3: Stopping and removing unhealthy worker...${NC}"
docker-compose -f docker-compose.dev.yml stop worker
docker rm -f 1f2e4615c35f 2>/dev/null || true
docker-compose -f docker-compose.dev.yml rm -f worker

echo -e "${GREEN}✓ Worker container removed${NC}"
echo ""

# Step 4: Restart worker
echo -e "${YELLOW}Step 4: Starting worker fresh...${NC}"
docker-compose -f docker-compose.dev.yml up -d worker

# Wait a bit
sleep 5

# Check status
echo ""
echo -e "${YELLOW}Step 5: Checking worker status...${NC}"
docker-compose -f docker-compose.dev.yml ps worker

echo ""
echo -e "${GREEN}=========================================="
echo "Worker Fix Complete!"
echo "==========================================${NC}"
echo ""
echo "If worker is still unhealthy, check:"
echo "1. Backend is running: docker-compose -f docker-compose.dev.yml ps backend"
echo "2. Redis is running: docker-compose -f docker-compose.dev.yml ps redis"
echo "3. Worker logs: docker-compose -f docker-compose.dev.yml logs -f worker"
echo ""

