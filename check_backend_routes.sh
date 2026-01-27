#!/bin/bash
# Check if backend routes are registered

echo "=== Checking Backend Routes ==="
echo ""

# Check if backend is running
if ! docker ps | grep -q "bot-prod-backend"; then
    echo "ERROR: Backend container is not running"
    exit 1
fi

echo "1. Checking backend logs for router registration..."
echo ""
docker logs bot-prod-backend 2>&1 | grep -i "router\|import\|warning\|error" | tail -20
echo ""

echo "2. Testing endpoints directly..."
echo ""

# Test tickets endpoint
echo "Testing /api/v1/tickets/demo/tickets..."
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/tickets/demo/tickets || echo "Failed to connect"
echo ""

# Test alerts endpoint  
echo "Testing /api/v1/alerts/alerts..."
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/alerts/alerts || echo "Failed to connect"
echo ""

# Test change-tickets endpoint
echo "Testing /api/v1/change-tickets..."
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/change-tickets || echo "Failed to connect"
echo ""

# Test agent pending-approvals endpoint
echo "Testing /api/v1/agent/pending-approvals..."
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/api/v1/agent/pending-approvals || echo "Failed to connect"
echo ""

echo "3. Checking FastAPI docs for registered routes..."
echo ""
echo "Visit http://localhost:8000/docs to see all registered endpoints"
echo ""

echo "4. Checking if modules can be imported..."
echo ""
docker exec bot-prod-backend python -c "
try:
    from app.api.v1.endpoints import ticket_ingestion, agent_execution, alerts, change_tickets
    print('✓ All modules imported successfully')
    print(f'  ticket_ingestion: {ticket_ingestion is not None}')
    print(f'  agent_execution: {agent_execution is not None}')
    print(f'  alerts: {alerts is not None}')
    print(f'  change_tickets: {change_tickets is not None}')
except ImportError as e:
    print(f'✗ Import failed: {e}')
except Exception as e:
    print(f'✗ Error: {e}')
" 2>&1

echo ""
echo "=== Done ==="
