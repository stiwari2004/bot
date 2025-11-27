# Quick script to get all ManageEngine data needed for Postman testing
Write-Host "Getting ManageEngine Postman Test Data..." -ForegroundColor Cyan
Write-Host ""

# Get access token
$token = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT meta_data::json->>'access_token' FROM ticketing_tool_connections WHERE tool_name = 'manageengine' LIMIT 1;" 2>&1 | Select-String -Pattern "^\s+[a-zA-Z0-9._-]+" | ForEach-Object { $_.Line.Trim() }

# Get API base URL
$apiUrl = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT api_base_url FROM ticketing_tool_connections WHERE tool_name = 'manageengine' LIMIT 1;" 2>&1 | Select-String -Pattern "^\s+[a-zA-Z0-9._-]+" | ForEach-Object { $_.Line.Trim() }

# Get a test ticket ID
$ticketId = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT external_id FROM tickets WHERE source = 'manageengine' ORDER BY created_at DESC LIMIT 1;" 2>&1 | Select-String -Pattern "^\s+[0-9]+" | ForEach-Object { $_.Line.Trim() }

if ($token) {
    Write-Host "✅ Access Token:" -ForegroundColor Green
    Write-Host $token -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "❌ No access token found" -ForegroundColor Red
    Write-Host ""
}

if ($apiUrl) {
    Write-Host "✅ API Base URL:" -ForegroundColor Green
    Write-Host $apiUrl -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "❌ No API URL found" -ForegroundColor Red
    Write-Host ""
}

if ($ticketId) {
    Write-Host "✅ Test Ticket ID:" -ForegroundColor Green
    Write-Host $ticketId -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "📋 Postman Request Details:" -ForegroundColor Cyan
    Write-Host "Method: PUT" -ForegroundColor White
    Write-Host "URL: $apiUrl/api/v3/requests/$ticketId" -ForegroundColor White
    Write-Host ""
    Write-Host "Headers:" -ForegroundColor White
    Write-Host "  Authorization: Zoho-oauthtoken $token" -ForegroundColor Gray
    Write-Host "  Accept: application/vnd.manageengine.sdp.v3+json" -ForegroundColor Gray
    Write-Host "  Content-Type: application/x-www-form-urlencoded" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Body (x-www-form-urlencoded):" -ForegroundColor White
    Write-Host "  Key: input_data" -ForegroundColor Gray
    Write-Host "  Value: {`"request`": {`"status`": {`"name`": `"Resolved`"}}}}" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "⚠️  No ticket ID found - you'll need to use a ticket ID from ManageEngine" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "📖 See MANAGEENGINE_POSTMAN_TEST.md for detailed test cases" -ForegroundColor Cyan

