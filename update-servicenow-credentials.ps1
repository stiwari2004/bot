# PowerShell script to update ServiceNow connection credentials
# Usage: .\update-servicenow-credentials.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [int]$ConnectionId
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Update ServiceNow Connection Credentials" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get existing connections
try {
    $connections = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
        -Method Get `
        -ContentType "application/json"
    
    $servicenowConn = $connections.connections | Where-Object { $_.tool_name -eq "servicenow" } | Select-Object -First 1
    
    if (-not $servicenowConn) {
        Write-Host "❌ No ServiceNow connection found" -ForegroundColor Red
        Write-Host "Please create a connection first using: .\create-servicenow-connection.ps1" -ForegroundColor Yellow
        exit 1
    }
    
    if (-not $ConnectionId) {
        $ConnectionId = $servicenowConn.id
    }
    
    Write-Host "Found ServiceNow connection:" -ForegroundColor Green
    Write-Host "  ID: $($servicenowConn.id)" -ForegroundColor White
    Write-Host "  Status: $($servicenowConn.last_sync_status)" -ForegroundColor $(if ($servicenowConn.last_sync_status -eq "success") { "Green" } else { "Red" })
    if ($servicenowConn.last_error) {
        Write-Host "  Error: $($servicenowConn.last_error)" -ForegroundColor Red
    }
    Write-Host ""
    
    # Get authentication method
    Write-Host "Authentication Method:" -ForegroundColor Cyan
    Write-Host "1. Basic Auth (Username/Password)" -ForegroundColor White
    Write-Host "2. OAuth 2.0 (Client ID/Secret)" -ForegroundColor White
    Write-Host ""
    $authChoice = Read-Host "Select authentication method (1 or 2)"
    
    $metaData = @{}
    
    if ($authChoice -eq "1") {
        $Username = Read-Host "Enter ServiceNow Username"
        $SecurePassword = Read-Host "Enter ServiceNow Password" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
        $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        $metaData.username = $Username
        $metaData.password = $Password
        
        # Also update api_username and api_password fields for ServiceNow
        $updateBody = @{
            meta_data = $metaData
            api_username = $Username
            api_password = $Password
        } | ConvertTo-Json -Depth 10
    } elseif ($authChoice -eq "2") {
        $ClientId = Read-Host "Enter OAuth Client ID"
        $SecureSecret = Read-Host "Enter OAuth Client Secret" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureSecret)
        $ClientSecret = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        $metaData.client_id = $ClientId
        $metaData.client_secret = $ClientSecret
        
        $updateBody = @{
            meta_data = $metaData
        } | ConvertTo-Json -Depth 10
    } else {
        Write-Host "❌ Error: Invalid choice. Please select 1 or 2" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Updating connection credentials..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections/$ConnectionId" `
            -Method Patch `
            -ContentType "application/json" `
            -Body $updateBody
        
        Write-Host "✅ Credentials updated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "1. Test the connection: .\test-servicenow-connection-api.ps1" -ForegroundColor White
        Write-Host "2. Or use API: POST $ApiBaseUrl/api/v1/settings/ticketing-connections/$ConnectionId/test" -ForegroundColor White
        Write-Host ""
        
    } catch {
        Write-Host "❌ Error updating credentials:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($errorDetails) {
                Write-Host "Details: $($errorDetails.detail)" -ForegroundColor Red
            }
        }
        exit 1
    }
    
} catch {
    Write-Host "❌ Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

