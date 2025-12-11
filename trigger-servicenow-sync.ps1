# PowerShell script to manually trigger ServiceNow sync
# This will actually fetch and create tickets in the database
# Usage: .\trigger-servicenow-sync.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [int]$ConnectionId
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Trigger ServiceNow Sync (Fetch & Create Tickets)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

try {
    # Get existing connections
    $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
        -Method Get `
        -ContentType "application/json"
    
    $allConnections = if ($response.connections) { $response.connections } else { $response }
    $servicenowConn = $allConnections | Where-Object { $_.tool_name -eq "servicenow" } | Select-Object -First 1
    
    if (-not $servicenowConn) {
        Write-Host "❌ No ServiceNow connection found" -ForegroundColor Red
        exit 1
    }
    
    if (-not $ConnectionId) {
        $ConnectionId = $servicenowConn.id
    }
    
    Write-Host "ServiceNow Connection:" -ForegroundColor Green
    Write-Host "  ID: $($servicenowConn.id)" -ForegroundColor White
    Write-Host "  API Base URL: $($servicenowConn.api_base_url)" -ForegroundColor White
    Write-Host "  Last Sync: $($servicenowConn.last_sync_at)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Note: The test endpoint only verifies connection." -ForegroundColor Yellow
    Write-Host "To actually create tickets, the poller service needs to run." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Checking if poller is running..." -ForegroundColor Cyan
    
    # Check backend logs for poller activity
    Write-Host ""
    Write-Host "To manually trigger sync, you can:" -ForegroundColor Yellow
    Write-Host "1. Wait for automatic sync (every $($servicenowConn.sync_interval_minutes) minutes)" -ForegroundColor White
    Write-Host "2. Restart the backend to trigger poller" -ForegroundColor White
    Write-Host "3. Check backend logs for poller activity" -ForegroundColor White
    Write-Host ""
    Write-Host "Checking recent poller activity..." -ForegroundColor Cyan
    
    # Try to check if we can see poller logs
    $logFile = "backend\logs\audit.log"
    if (Test-Path $logFile) {
        $recentLogs = Get-Content $logFile -Tail 50 | Select-String -Pattern "poller|Polled.*servicenow" -Context 0
        if ($recentLogs) {
            Write-Host "Recent poller activity found:" -ForegroundColor Green
            $recentLogs | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        } else {
            Write-Host "⚠️  No recent poller activity found" -ForegroundColor Yellow
            Write-Host "   The poller may not be running or hasn't synced yet" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "To verify tickets were created, check:" -ForegroundColor Yellow
    Write-Host "  GET $ApiBaseUrl/api/v1/tickets/demo/tickets?limit=100" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}









