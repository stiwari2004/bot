#!/bin/bash
# Verify backend code has the router logging

echo "=== Verifying Backend Code ==="
echo ""

# Check if backend is running
if ! docker ps | grep -q "bot-prod-backend"; then
    echo "ERROR: Backend container is not running"
    exit 1
fi

echo "1. Checking if router logging code exists in container..."
echo ""
docker exec bot-prod-backend grep -n "Registered ticket_ingestion router" /app/app/api/v1/api.py 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "✓ Router logging code found in container"
else
    echo "✗ Router logging code NOT found - backend needs rebuild"
fi
echo ""

echo "2. Checking if import logging exists..."
echo ""
docker exec bot-prod-backend grep -n "Successfully imported Phase 2 endpoints" /app/app/api/v1/api.py 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "✓ Import logging code found in container"
else
    echo "✗ Import logging code NOT found - backend needs rebuild"
fi
echo ""

echo "3. Testing module imports directly..."
echo ""
docker exec bot-prod-backend python -c "
import sys
sys.path.insert(0, '/app')
try:
    from app.api.v1.endpoints import ticket_ingestion, agent_execution, alerts, change_tickets
    print('✓ All modules imported successfully')
    print(f'  ticket_ingestion: {ticket_ingestion is not None}')
    print(f'  agent_execution: {agent_execution is not None}')
    print(f'  alerts: {alerts is not None}')
    print(f'  change_tickets: {change_tickets is not None}')
    
    if ticket_ingestion:
        print(f'  ticket_ingestion.router: {hasattr(ticket_ingestion, \"router\")}')
    if agent_execution:
        print(f'  agent_execution.router: {hasattr(agent_execution, \"router\")}')
    if alerts:
        print(f'  alerts.router: {hasattr(alerts, \"router\")}')
    if change_tickets:
        print(f'  change_tickets.router: {hasattr(change_tickets, \"router\")}')
except ImportError as e:
    print(f'✗ Import failed: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

echo ""
echo "4. Checking startup logs for router registration (full startup)..."
echo ""
docker logs bot-prod-backend 2>&1 | grep -A 5 -B 5 "Application startup complete" | tail -30

echo ""
echo "=== Done ==="
echo ""
echo "If router logging code is missing, rebuild backend with:"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod build backend"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod up -d backend"
