# Comprehensive ManageEngine Connection Diagnostic Script
Write-Host "=== ManageEngine Connection Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check connection in database
Write-Host "1. Checking database connection..." -ForegroundColor Yellow
$connectionInfo = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, tool_name, is_active, connection_type, api_base_url, last_sync_at, last_sync_status, last_error FROM ticketing_tool_connections WHERE tool_name = 'manageengine';" 2>&1

if ($connectionInfo -match "0 rows") {
    Write-Host "   ❌ No ManageEngine connection found in database" -ForegroundColor Red
    Write-Host "   → Create a connection first via the UI or API" -ForegroundColor Yellow
    exit
} else {
    Write-Host "   ✅ Connection found:" -ForegroundColor Green
    Write-Host $connectionInfo
}

Write-Host ""

# 2. Check if poller is enabled
Write-Host "2. Checking if poller is enabled..." -ForegroundColor Yellow
$pollerEnabled = docker-compose exec -T backend printenv ENABLE_TICKETING_POLLER 2>&1
if ($pollerEnabled -match "false|0|no") {
    Write-Host "   ⚠️  Poller is DISABLED (ENABLE_TICKETING_POLLER=$pollerEnabled)" -ForegroundColor Yellow
    Write-Host "   → Set ENABLE_TICKETING_POLLER=true in docker-compose.yml or .env" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ Poller is enabled" -ForegroundColor Green
}

Write-Host ""

# 3. Check poller logs
Write-Host "3. Checking recent poller logs..." -ForegroundColor Yellow
$pollerLogs = docker-compose logs backend --tail=50 2>&1 | Select-String -Pattern "poller|Polling.*manageengine|Error polling" -Context 1,1
if ($pollerLogs) {
    Write-Host "   Recent poller activity:" -ForegroundColor Green
    $pollerLogs | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   ⚠️  No recent poller activity found" -ForegroundColor Yellow
}

Write-Host ""

# 4. Check connection type
Write-Host "4. Checking connection type..." -ForegroundColor Yellow
$connectionType = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT connection_type FROM ticketing_tool_connections WHERE tool_name = 'manageengine' LIMIT 1;" 2>&1 | Select-String -Pattern "api_poll|webhook|api_push"
if ($connectionType -match "api_poll") {
    Write-Host "   ✅ Connection type is 'api_poll' (correct for polling)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Connection type is NOT 'api_poll' (current: $connectionType)" -ForegroundColor Red
    Write-Host "   → Update connection_type to 'api_poll' for automatic polling" -ForegroundColor Yellow
    Write-Host "   → Or use webhook/API push if you prefer real-time updates" -ForegroundColor Yellow
}

Write-Host ""

# 5. Test connection via API
Write-Host "5. Testing connection via API..." -ForegroundColor Yellow
Write-Host "   (This requires the connection ID from step 1)" -ForegroundColor Gray
Write-Host "   Run: curl -X POST http://localhost:8000/api/v1/ticketing-connections/{connection_id}/test" -ForegroundColor Cyan

Write-Host ""
Write-Host "=== Diagnostic Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Common Issues:" -ForegroundColor Yellow
Write-Host "1. Connection type must be 'api_poll' for automatic polling" -ForegroundColor White
Write-Host "2. Connection must be active (is_active = true)" -ForegroundColor White
Write-Host "3. Poller must be enabled (ENABLE_TICKETING_POLLER=true)" -ForegroundColor White
Write-Host "4. Connection must have valid OAuth tokens" -ForegroundColor White
Write-Host "5. Poller runs every 1 minute, but syncs based on sync_interval_minutes" -ForegroundColor White

