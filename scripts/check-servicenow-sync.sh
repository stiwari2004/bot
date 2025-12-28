#!/bin/bash
# Diagnostic script to check ServiceNow sync status

echo "=== ServiceNow Sync Diagnostic ==="
echo ""

# 1. Check if poller is enabled
echo "1. Checking if poller is enabled..."
POLLER_ENABLED=$(docker compose -f docker-compose.production.yml exec -T backend printenv ENABLE_TICKETING_POLLER 2>/dev/null || echo "true")
if [ -z "$POLLER_ENABLED" ] || [ "$POLLER_ENABLED" = "true" ]; then
    echo "   ✅ Poller is enabled (ENABLE_TICKETING_POLLER=${POLLER_ENABLED:-true})"
else
    echo "   ⚠️  Poller is DISABLED (ENABLE_TICKETING_POLLER=$POLLER_ENABLED)"
    echo "   → Set ENABLE_TICKETING_POLLER=true in docker-compose.production.yml"
fi
echo ""

# 2. Check poller startup in logs
echo "2. Checking if poller started..."
POLLER_STARTED=$(docker compose -f docker-compose.production.yml logs backend 2>/dev/null | grep -i "ticketing poller service started" | tail -1)
if [ -n "$POLLER_STARTED" ]; then
    echo "   ✅ Poller started: $POLLER_STARTED"
else
    echo "   ⚠️  No poller startup message found in logs"
fi
echo ""

# 3. Check connection configuration in database
echo "3. Checking ServiceNow connection configuration..."
CONNECTION_INFO=$(docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, tool_name, is_active, connection_type, sync_interval_minutes, last_sync_at, last_sync_status, last_error FROM ticketing_tool_connections WHERE tool_name = 'servicenow';" 2>&1)

if echo "$CONNECTION_INFO" | grep -q "0 rows"; then
    echo "   ❌ No ServiceNow connection found in database"
    echo "   → Create a connection first via the UI or API"
else
    echo "   Connection details:"
    echo "$CONNECTION_INFO" | grep -v "rows\|----\|id\|^$" | head -5
fi
echo ""

# 4. Check recent poller activity
echo "4. Checking recent poller activity (last 100 lines)..."
POLLER_LOGS=$(docker compose -f docker-compose.production.yml logs backend --tail=100 2>/dev/null | grep -iE "polling|servicenow|ticket.*created|ticket.*updated|Error polling" | tail -10)
if [ -n "$POLLER_LOGS" ]; then
    echo "   Recent poller activity:"
    echo "$POLLER_LOGS" | sed 's/^/   /'
else
    echo "   ⚠️  No recent poller activity found"
    echo "   → The poller may not be running or no connections match the criteria"
fi
echo ""

# 5. Check ticket count
echo "5. Checking ticket count in database..."
TICKET_COUNT=$(docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -t -c "SELECT COUNT(*) FROM tickets WHERE source = 'servicenow';" 2>&1 | tr -d ' ')
if [ -n "$TICKET_COUNT" ] && [ "$TICKET_COUNT" != "0" ]; then
    echo "   ✅ Found $TICKET_COUNT ServiceNow tickets in database"
else
    echo "   ⚠️  No ServiceNow tickets found in database (count: ${TICKET_COUNT:-0})"
fi
echo ""

# 6. Recommendations
echo "=== Recommendations ==="
echo ""
echo "If tickets are not syncing:"
echo "1. Ensure connection is active: is_active = true"
echo "2. Ensure connection_type = 'api_poll'"
echo "3. Check backend logs: docker compose -f docker-compose.production.yml logs backend --tail=200 | grep -i poller"
echo "4. Manually trigger sync: POST /api/v1/settings/ticketing-connections/{id}/sync"
echo ""



