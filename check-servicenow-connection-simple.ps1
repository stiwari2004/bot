# Simple PowerShell script to check ServiceNow connection status
# Usage: .\check-servicenow-connection-simple.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000"
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "ServiceNow Connection Status Check" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
        -Method Get `
        -ContentType "application/json"
    
    # API returns { "connections": [...] }, so we need to access .connections
    $allConnections = if ($response.connections) { $response.connections } else { $response }
    $servicenowConnections = $allConnections | Where-Object { $_.tool_name -eq "servicenow" }
    
    if (-not $servicenowConnections -or $servicenowConnections.Count -eq 0) {
        Write-Host "❌ No ServiceNow connections found" -ForegroundColor Red
        Write-Host ""
        Write-Host "To create a connection:" -ForegroundColor Yellow
        Write-Host "1. Use the UI: Settings > Ticketing Connections > Add Connection" -ForegroundColor White
        Write-Host "2. Use PowerShell: .\create-servicenow-connection.ps1" -ForegroundColor White
        Write-Host "3. Use API: POST $ApiBaseUrl/api/v1/ticketing-connections" -ForegroundColor White
        exit 0
    }
    
    Write-Host "✅ Found $($servicenowConnections.Count) ServiceNow connection(s)" -ForegroundColor Green
    Write-Host ""
    
    foreach ($conn in $servicenowConnections) {
        Write-Host "Connection Details:" -ForegroundColor Cyan
        Write-Host "  ID: $($conn.id)" -ForegroundColor White
        Write-Host "  Tool: $($conn.tool_name)" -ForegroundColor White
        Write-Host "  Type: $($conn.connection_type)" -ForegroundColor White
        Write-Host "  Active: $($conn.is_active)" -ForegroundColor $(if ($conn.is_active) { "Green" } else { "Red" })
        Write-Host "  API Base URL: $($conn.api_base_url)" -ForegroundColor White
        Write-Host "  Sync Interval: $($conn.sync_interval_minutes) minutes" -ForegroundColor White
        Write-Host "  Last Sync: $($conn.last_sync_at)" -ForegroundColor White
        Write-Host "  Last Status: $($conn.last_sync_status)" -ForegroundColor $(if ($conn.last_sync_status -eq "success") { "Green" } else { "Red" })
        if ($conn.last_error) {
            Write-Host "  Last Error: $($conn.last_error)" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "-" * 60 -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "To test the connection:" -ForegroundColor Yellow
    Write-Host "  .\test-servicenow-connection-api.ps1" -ForegroundColor White
    Write-Host "  Or API: POST $ApiBaseUrl/api/v1/settings/ticketing-connections/$($servicenowConnections[0].id)/test" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ Error checking connections:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($errorDetails) {
            Write-Host "Details: $($errorDetails.detail)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "Make sure the backend API is running on $ApiBaseUrl" -ForegroundColor Yellow
    exit 1
}

