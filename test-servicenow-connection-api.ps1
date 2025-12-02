# PowerShell script to test ServiceNow connection via API
# Usage: .\test-servicenow-connection-api.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [int]$ConnectionId
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "ServiceNow Connection Test (via API)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

try {
    # Get existing connections
    $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
        -Method Get `
        -ContentType "application/json"
    
    # API returns { "connections": [...] }, so we need to access .connections
    $allConnections = if ($response.connections) { $response.connections } else { $response }
    $servicenowConn = $allConnections | Where-Object { $_.tool_name -eq "servicenow" } | Select-Object -First 1
    
    if (-not $servicenowConn) {
        Write-Host "❌ No ServiceNow connection found" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please create a connection first:" -ForegroundColor Yellow
        Write-Host "  .\create-servicenow-connection.ps1 -InstanceUrl `"https://your-instance.service-now.com`"" -ForegroundColor White
        exit 1
    }
    
    if (-not $ConnectionId) {
        $ConnectionId = $servicenowConn.id
    }
    
    Write-Host "Found ServiceNow connection:" -ForegroundColor Green
    Write-Host "  ID: $($servicenowConn.id)" -ForegroundColor White
    Write-Host "  API Base URL: $($servicenowConn.api_base_url)" -ForegroundColor White
    Write-Host "  Active: $($servicenowConn.is_active)" -ForegroundColor $(if ($servicenowConn.is_active) { "Green" } else { "Red" })
    Write-Host "  Last Status: $($servicenowConn.last_sync_status)" -ForegroundColor $(if ($servicenowConn.last_sync_status -eq "success") { "Green" } else { "Red" })
    if ($servicenowConn.last_error) {
        Write-Host "  Last Error: $($servicenowConn.last_error)" -ForegroundColor Red
    }
    Write-Host ""
    
    Write-Host "Testing connection..." -ForegroundColor Cyan
    Write-Host "-" * 60 -ForegroundColor Gray
    Write-Host ""
    
    # Test the connection
    try {
        $testResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections/$ConnectionId/test" `
            -Method Post `
            -ContentType "application/json"
        
        if ($testResponse.status -eq "success") {
            Write-Host "✅ Connection test successful!" -ForegroundColor Green
            Write-Host "   Message: $($testResponse.message)" -ForegroundColor White
            Write-Host "   Tickets Fetched: $($testResponse.tickets_fetched)" -ForegroundColor White
            Write-Host ""
            Write-Host "=" * 60 -ForegroundColor Green
            Write-Host "✅ ServiceNow connection is working!" -ForegroundColor Green
            Write-Host "=" * 60 -ForegroundColor Green
        } elseif ($testResponse.status -eq "oauth_required") {
            Write-Host "⚠️  OAuth authorization required" -ForegroundColor Yellow
            Write-Host "   Message: $($testResponse.message)" -ForegroundColor White
            Write-Host ""
            Write-Host "Please authorize the connection first." -ForegroundColor Yellow
        } else {
            Write-Host "❌ Connection test failed" -ForegroundColor Red
            Write-Host "   Status: $($testResponse.status)" -ForegroundColor Red
            Write-Host "   Message: $($testResponse.message)" -ForegroundColor Red
            Write-Host ""
            Write-Host "Troubleshooting:" -ForegroundColor Yellow
            Write-Host "1. Verify ServiceNow instance URL is correct" -ForegroundColor White
            Write-Host "2. Check credentials (username/password or OAuth)" -ForegroundColor White
            Write-Host "3. Ensure service account has required roles" -ForegroundColor White
            Write-Host "4. Check ServiceNow instance is accessible" -ForegroundColor White
        }
        
    } catch {
        Write-Host "❌ Error testing connection:" -ForegroundColor Red
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
        Write-Host "1. Make sure backend API is running on $ApiBaseUrl" -ForegroundColor White
        Write-Host "2. Check if connection has valid credentials" -ForegroundColor White
        Write-Host "3. Try updating credentials: .\update-servicenow-credentials.ps1" -ForegroundColor White
    }
    
} catch {
    Write-Host "❌ Error:" -ForegroundColor Red
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

