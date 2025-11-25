# PowerShell script to test OAuth flow

Write-Host "Step 1: Getting authorization URL from backend..." -ForegroundColor Green
$authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/settings/ticketing-connections/7/oauth/authorize" -Method Get
Write-Host "Authorization URL:" -ForegroundColor Yellow
Write-Host $authResponse.authorization_url -ForegroundColor Cyan
Write-Host "`nState:" -ForegroundColor Yellow
Write-Host $authResponse.state -ForegroundColor Cyan
Write-Host "`nCopy the authorization_url above and open it in your browser." -ForegroundColor Green
Write-Host "After authorization, you'll be redirected. Copy the 'code' parameter from the URL.`n" -ForegroundColor Green

# Step 2: Get client secret
Write-Host "Step 2: Getting client secret from database..." -ForegroundColor Green
$clientSecret = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT meta_data::json->>'client_secret' as client_secret FROM ticketing_tool_connections WHERE id = 7;" | Select-String -Pattern "^\s+[a-zA-Z0-9._-]+$" | ForEach-Object { $_.Line.Trim() }
Write-Host "Client Secret retrieved (first 10 chars): $($clientSecret.Substring(0, [Math]::Min(10, $clientSecret.Length)))..." -ForegroundColor Yellow

# Step 3: Prompt for authorization code
Write-Host "`nStep 3: Enter the authorization code from the redirect URL:" -ForegroundColor Green
$authCode = Read-Host "Authorization Code"

# Step 4: Exchange code for tokens
Write-Host "`nStep 4: Exchanging code for tokens..." -ForegroundColor Green
$tokenUrl = "https://accounts.zoho.in/oauth/v2/token"
$body = @{
    grant_type = "authorization_code"
    client_id = "1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK"
    client_secret = $clientSecret
    redirect_uri = "http://localhost:8000/oauth/callback"
    code = $authCode
}

try {
    $tokenResponse = Invoke-RestMethod -Uri $tokenUrl -Method Post -Body $body -ContentType "application/x-www-form-urlencoded"
    
    Write-Host "`n=== TOKEN EXCHANGE RESPONSE ===" -ForegroundColor Green
    Write-Host "Response Keys: $($tokenResponse.PSObject.Properties.Name -join ', ')" -ForegroundColor Yellow
    
    if ($tokenResponse.refresh_token) {
        Write-Host "`n✅ SUCCESS: refresh_token IS present in response!" -ForegroundColor Green
        Write-Host "refresh_token length: $($tokenResponse.refresh_token.Length)" -ForegroundColor Cyan
    } else {
        Write-Host "`n❌ PROBLEM: refresh_token is NOT in the response!" -ForegroundColor Red
        Write-Host "This means Zoho is not returning it." -ForegroundColor Yellow
    }
    
    Write-Host "`nFull Response:" -ForegroundColor Yellow
    $tokenResponse | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "`n❌ ERROR during token exchange:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Error Details:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}



