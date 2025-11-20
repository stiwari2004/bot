# Quick script to get ManageEngine OAuth token from database
Write-Host "Getting ManageEngine OAuth token..." -ForegroundColor Cyan

$token = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT meta_data::json->>'access_token' FROM ticketing_tool_connections WHERE tool_name = 'manageengine' LIMIT 1;" 2>&1 | Select-String -Pattern "^\s+[a-zA-Z0-9._-]+" | ForEach-Object { $_.Line.Trim() }

if ($token) {
    Write-Host "`nAccess Token:" -ForegroundColor Green
    Write-Host $token -ForegroundColor Yellow
    Write-Host "`nCopy this token for Postman testing!" -ForegroundColor Cyan
} else {
    Write-Host "`nNo token found. Make sure OAuth authorization completed." -ForegroundColor Red
}





