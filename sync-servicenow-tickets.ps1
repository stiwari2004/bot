# PowerShell script to manually sync ServiceNow tickets (actually creates tickets in database)
# Usage: .\sync-servicenow-tickets.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [int]$ConnectionId
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Manual ServiceNow Ticket Sync" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "This will fetch incidents from ServiceNow and CREATE tickets in the database" -ForegroundColor Yellow
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
    Write-Host "  Active: $($servicenowConn.is_active)" -ForegroundColor $(if ($servicenowConn.is_active) { "Green" } else { "Red" })
    Write-Host "  Last Sync: $($servicenowConn.last_sync_at)" -ForegroundColor White
    Write-Host "  Last Status: $($servicenowConn.last_sync_status)" -ForegroundColor $(if ($servicenowConn.last_sync_status -eq "success") { "Green" } else { "Red" })
    Write-Host ""
    
    if (-not $servicenowConn.is_active) {
        Write-Host "❌ Connection is not active. Please activate it first." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Triggering manual sync..." -ForegroundColor Cyan
    Write-Host "-" * 60 -ForegroundColor Gray
    Write-Host ""
    
    # Trigger manual sync
    try {
        $syncResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections/$ConnectionId/sync" `
            -Method Post `
            -ContentType "application/json"
        
        if ($syncResponse.status -eq "success") {
            Write-Host "✅ Sync completed successfully!" -ForegroundColor Green
            Write-Host "   Message: $($syncResponse.message)" -ForegroundColor White
            Write-Host "   Last Sync: $($syncResponse.last_sync_at)" -ForegroundColor White
            Write-Host "   Status: $($syncResponse.last_sync_status)" -ForegroundColor Green
            Write-Host ""
            Write-Host "=" * 60 -ForegroundColor Green
            Write-Host "✅ Tickets should now be in the database!" -ForegroundColor Green
            Write-Host "=" * 60 -ForegroundColor Green
            Write-Host ""
            Write-Host "Check tickets:" -ForegroundColor Yellow
            Write-Host "  GET $ApiBaseUrl/api/v1/tickets/demo/tickets?limit=100" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "❌ Sync failed" -ForegroundColor Red
            Write-Host "   Status: $($syncResponse.status)" -ForegroundColor Red
            Write-Host "   Message: $($syncResponse.message)" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "❌ Error triggering sync:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($errorDetails) {
                Write-Host "Details: $($errorDetails.detail)" -ForegroundColor Red
            } else {
                Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
            }
        }
        
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Make sure backend API is running" -ForegroundColor White
        Write-Host "2. Verify connection is active" -ForegroundColor White
        Write-Host "3. Check connection has valid credentials" -ForegroundColor White
        exit 1
    }
    
} catch {
    Write-Host "❌ Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}


