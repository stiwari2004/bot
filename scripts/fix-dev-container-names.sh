#!/bin/bash
# Fix dev container names to avoid conflicts with production

set -e

echo "=========================================="
echo "Fixing Dev Container Names"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Step 1: Stopping all dev containers...${NC}"
docker-compose -f docker-compose.dev.yml down

echo ""
echo -e "${YELLOW}Step 2: Removing any containers with conflicting names...${NC}"

# Remove any containers that might conflict
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-worker bot-dev-frontend 2>/dev/null || true

# Also remove any old containers with generic names that might conflict
docker ps -a | grep "bot.*postgres" | grep -v "bot-dev-postgres" | grep -v "bot_postgres_1" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo -e "${YELLOW}Step 3: Starting dev containers with proper names...${NC}"
docker-compose -f docker-compose.dev.yml up -d

echo ""
echo -e "${YELLOW}Step 4: Verifying container names...${NC}"
echo ""

# Check dev containers
echo "Dev containers:"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "Production containers (should be separate):"
docker-compose -f docker-compose.production.yml ps 2>/dev/null || echo "Production not running (this is OK)"

echo ""
echo -e "${GREEN}=========================================="
echo "Container Names Fixed!"
echo "==========================================${NC}"
echo ""
echo "Dev containers now use names:"
echo "  - bot-dev-postgres"
echo "  - bot-dev-redis"
echo "  - bot-dev-backend"
echo "  - bot-dev-worker"
echo "  - bot-dev-frontend"
echo ""
echo "These will NOT conflict with production containers."
echo ""

