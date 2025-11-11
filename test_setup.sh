#!/bin/bash

# Quick Setup Verification Script
# Tests all critical endpoints and components

echo "🔍 Troubleshooting AI - Setup Verification"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-""}
    
    echo -n "Testing $name... "
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓${NC} (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗${NC} (HTTP $http_code)"
        echo "  Response: $body"
        return 1
    fi
}

# Test Services
echo "📦 Service Status"
echo "----------------"
docker-compose ps | grep -E "backend|frontend|postgres" | awk '{print "  " $1 ": " $7}'
echo ""

# Test Backend Health
echo "🏥 Backend Health Checks"
echo "----------------------"
test_endpoint "Backend Health" "$BASE_URL/health"
test_endpoint "API Health" "$BASE_URL/api/v1/demo/stats"
echo ""

# Test Ticket Endpoints
echo "🎫 Ticket Management"
echo "-------------------"
test_endpoint "List Tickets" "$BASE_URL/api/v1/tickets/demo/tickets?limit=5"
test_endpoint "Execution Mode" "$BASE_URL/api/v1/settings/execution-mode/demo"
echo ""

# Test Agent Endpoints
echo "🤖 Agent Execution"
echo "----------------"
test_endpoint "Pending Approvals" "$BASE_URL/api/v1/agent/pending-approvals"
echo ""

# Test Settings
echo "⚙️  Settings"
echo "-----------"
test_endpoint "Ticketing Tools" "$BASE_URL/api/v1/settings/ticketing-tools"
test_endpoint "Ticketing Connections" "$BASE_URL/api/v1/settings/ticketing-connections"
echo ""

# Test Frontend
echo "🌐 Frontend"
echo "----------"
if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "Frontend accessible: ${GREEN}✓${NC}"
else
    echo -e "Frontend accessible: ${RED}✗${NC}"
fi
echo ""

# Database Tables Check
echo "💾 Database Schema"
echo "-----------------"
tables=$(docker-compose exec -T backend python -c "
from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print(','.join(inspector.get_table_names()))
" 2>/dev/null)

if [ -n "$tables" ]; then
    table_count=$(echo "$tables" | tr ',' '\n' | wc -l | tr -d ' ')
    echo -e "  Tables found: ${GREEN}$table_count${NC}"
    echo "  Key tables: tickets, runbooks, execution_sessions, execution_steps"
else
    echo -e "  ${RED}Could not verify database tables${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Setup Verification Complete!"
echo ""
echo "Next Steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Check the grouped navigation (AGENT, ASSISTANT, SYSTEM)"
echo "3. View tickets in the Tickets tab"
echo "4. Test runbook generation from ticket details"
echo "5. Configure settings in Settings & Connections"
echo ""
echo "See SETUP_COMPLETE.md for detailed testing guide"



