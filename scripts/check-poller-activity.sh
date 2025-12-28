#!/bin/bash
# Quick script to check poller activity and connection status

echo "=== Poller Activity Check ==="
echo ""

# 1. Check if poller is running (look for recent activity)
echo "1. Checking recent poller activity (last 2 minutes)..."
RECENT_ACTIVITY=$(docker compose -f docker-compose.production.yml logs backend --since 2m 2>/dev/null | grep -iE "polling|servicenow|ticket.*created|ticket.*updated|Error polling" | tail -20)
if [ -n "$RECENT_ACTIVITY" ]; then
    echo "   ✅ Recent poller activity found:"
    echo "$RECENT_ACTIVITY" | sed 's/^/   /'
else
    echo "   ⚠️  No recent poller activity (poller may be waiting for sync interval)"
fi
echo ""

# 2. Check ServiceNow connection status
echo "2. ServiceNow Connection Status:"
CONNECTION_STATUS=$(docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, tool_name, is_active, connection_type, sync_interval_minutes, last_sync_at, last_sync_status, LEFT(last_error, 100) as error_preview FROM ticketing_tool_connections WHERE tool_name = 'servicenow';" 2>&1)
echo "$CONNECTION_STATUS" | grep -v "rows\|----\|^$" | head -10
echo ""

# 3. Check ticket count
echo "3. ServiceNow Tickets in Database:"
TICKET_COUNT=$(docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -t -c "SELECT COUNT(*) FROM tickets WHERE source = 'servicenow';" 2>&1 | tr -d ' ')
echo "   Total ServiceNow tickets: ${TICKET_COUNT:-0}"
echo ""

# 4. Check last few tickets
if [ -n "$TICKET_COUNT" ] && [ "$TICKET_COUNT" != "0" ]; then
    echo "4. Recent ServiceNow tickets (last 5):"
    docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, external_id, title, status, created_at FROM tickets WHERE source = 'servicenow' ORDER BY created_at DESC LIMIT 5;" 2>&1 | grep -v "rows\|----\|^$" | head -10
else
    echo "4. No tickets found yet. Poller may still be syncing..."
fi
echo ""

# 5. Recommendations
echo "=== Next Steps ==="
echo ""
echo "If no tickets are syncing:"
echo "1. Wait 1-2 minutes (default sync interval is 1 minute)"
echo "2. Check connection: is_active=true, connection_type='api_poll'"
echo "3. Manually trigger sync: POST /api/v1/settings/ticketing-connections/{id}/sync"
echo "4. Check full logs: docker compose -f docker-compose.production.yml logs backend --tail=500 | grep -i servicenow"
echo ""



