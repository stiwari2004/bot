# Check backend logs for token exchange information

Write-Host "Checking backend logs for Zoho token exchange response..." -ForegroundColor Green
Write-Host "Looking for: 'Zoho token response keys', 'refresh_token', 'token exchange'" -ForegroundColor Yellow
Write-Host ""

# Get recent logs
$logs = docker-compose logs backend --tail 500 2>&1

# Search for relevant lines
$relevantLogs = $logs | Select-String -Pattern "Zoho token response|refresh_token|token exchange|OAuth authorization successful" -CaseSensitive:$false -Context 0,3

if ($relevantLogs) {
    Write-Host "=== RELEVANT LOG ENTRIES ===" -ForegroundColor Green
    $relevantLogs | ForEach-Object {
        Write-Host $_.Line -ForegroundColor Cyan
        if ($_.Context.PostContext) {
            $_.Context.PostContext | ForEach-Object {
                Write-Host $_ -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
} else {
    Write-Host "No relevant log entries found. Trying to get all recent logs..." -ForegroundColor Yellow
    docker-compose logs backend --tail 100
}



