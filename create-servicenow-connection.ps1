# PowerShell script to create ServiceNow connection
# Usage: .\create-servicenow-connection.ps1 -InstanceUrl "https://your-instance.service-now.com" -Username "your-username" -Password "your-password"
# OR for OAuth: .\create-servicenow-connection.ps1 -InstanceUrl "https://your-instance.service-now.com" -ClientId "your-client-id" -ClientSecret "your-client-secret"

param(
    [Parameter(Mandatory=$true)]
    [string]$InstanceUrl,
    
    [Parameter(Mandatory=$false)]
    [string]$Username,
    
    [Parameter(Mandatory=$false)]
    [string]$Password,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientSecret,
    
    [Parameter(Mandatory=$false)]
    [int]$SyncIntervalMinutes = 5,
    
    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "http://localhost:8000"
)

# If credentials not provided, prompt for them
if (-not $Username -and -not $ClientId) {
    Write-Host ""
    Write-Host "Authentication Method:" -ForegroundColor Cyan
    Write-Host "1. Basic Auth (Username/Password)" -ForegroundColor White
    Write-Host "2. OAuth 2.0 (Client ID/Secret)" -ForegroundColor White
    Write-Host ""
    $authChoice = Read-Host "Select authentication method (1 or 2)"
    
    if ($authChoice -eq "1") {
        $Username = Read-Host "Enter ServiceNow Username"
        $SecurePassword = Read-Host "Enter ServiceNow Password" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
        $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    } elseif ($authChoice -eq "2") {
        $ClientId = Read-Host "Enter OAuth Client ID"
        $SecureSecret = Read-Host "Enter OAuth Client Secret" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureSecret)
        $ClientSecret = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    } else {
        Write-Host "❌ Error: Invalid choice. Please select 1 or 2" -ForegroundColor Red
        exit 1
    }
}

# Validate parameters
if (-not $Username -and -not $ClientId) {
    Write-Host "❌ Error: Either Username/Password (Basic Auth) or ClientId/ClientSecret (OAuth) must be provided" -ForegroundColor Red
    exit 1
}

if ($Username -and -not $Password) {
    Write-Host "❌ Error: Password is required when using Username" -ForegroundColor Red
    exit 1
}

if ($ClientId -and -not $ClientSecret) {
    Write-Host "❌ Error: ClientSecret is required when using ClientId" -ForegroundColor Red
    exit 1
}

# Build request body
$metaData = @{}

if ($Username) {
    Write-Host "Using Basic Auth..." -ForegroundColor Yellow
    $metaData.username = $Username
    $metaData.password = $Password
} else {
    Write-Host "Using OAuth 2.0..." -ForegroundColor Yellow
    $metaData.client_id = $ClientId
    $metaData.client_secret = $ClientSecret
}

$body = @{
    tool_name = "servicenow"
    connection_type = "api_poll"
    api_base_url = $InstanceUrl
    sync_interval_minutes = $SyncIntervalMinutes
    meta_data = $metaData
} | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "Creating ServiceNow connection..." -ForegroundColor Cyan
Write-Host "Instance URL: $InstanceUrl" -ForegroundColor Gray
Write-Host "Sync Interval: $SyncIntervalMinutes minutes" -ForegroundColor Gray
Write-Host ""

try {
    # Check if connection already exists
    try {
        $existing = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
            -Method Get `
            -ContentType "application/json"
        
        $servicenowConn = $existing.connections | Where-Object { $_.tool_name -eq "servicenow" } | Select-Object -First 1
        
        if ($servicenowConn) {
            Write-Host "⚠️  ServiceNow connection already exists (ID: $($servicenowConn.id))" -ForegroundColor Yellow
            Write-Host "   Status: $($servicenowConn.last_sync_status)" -ForegroundColor $(if ($servicenowConn.last_sync_status -eq "success") { "Green" } else { "Red" })
            if ($servicenowConn.last_error) {
                Write-Host "   Error: $($servicenowConn.last_error)" -ForegroundColor Red
            }
            Write-Host ""
            $update = Read-Host "Do you want to update this connection with new credentials? (y/n)"
            
            if ($update -eq "y" -or $update -eq "Y") {
                Write-Host "Updating existing connection..." -ForegroundColor Cyan
                $updateBody = @{
                    meta_data = $metaData
                } | ConvertTo-Json -Depth 10
                
                $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections/$($servicenowConn.id)" `
                    -Method Patch `
                    -ContentType "application/json" `
                    -Body $updateBody
                
                Write-Host "✅ Connection updated successfully!" -ForegroundColor Green
                Write-Host ""
                Write-Host "Connection ID: $($servicenowConn.id)" -ForegroundColor Cyan
                Write-Host "Next steps:" -ForegroundColor Yellow
                Write-Host "1. Test the connection: .\test-servicenow-connection-api.ps1" -ForegroundColor White
                Write-Host "2. Or use API: POST $ApiBaseUrl/api/v1/settings/ticketing-connections/$($servicenowConn.id)/test" -ForegroundColor White
                exit 0
            } else {
                Write-Host "Skipping update. Exiting." -ForegroundColor Yellow
                exit 0
            }
        }
    } catch {
        # If GET fails, continue to create new connection
        Write-Host "Could not check existing connections, proceeding to create new..." -ForegroundColor Yellow
    }
    
    $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/settings/ticketing-connections" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "✅ Connection created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Connection ID: $($response.id)" -ForegroundColor Cyan
    Write-Host "Tool: $($response.tool_name)" -ForegroundColor Cyan
    Write-Host "Status: $($response.is_active)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the connection: .\test-servicenow-connection-api.ps1" -ForegroundColor White
    Write-Host "2. Or use API: POST $ApiBaseUrl/api/v1/settings/ticketing-connections/$($response.id)/test" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ Error creating connection:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "Details: $($errorDetails.detail)" -ForegroundColor Red
    }
    
    exit 1
}

