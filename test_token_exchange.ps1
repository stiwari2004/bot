# Test token exchange with the authorization code we found

# Get client secret from database
Write-Host "Getting client secret from database..." -ForegroundColor Yellow
$secretOutput = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -t -A -c "SELECT meta_data::json->>'client_secret' FROM ticketing_tool_connections WHERE id = 7;" 2>&1
# Filter out docker-compose warnings and get just the secret (last non-empty line)
$clientSecret = ($secretOutput | Where-Object { $_ -notmatch 'level=warning' -and $_ -notmatch '^time=' -and $_.Trim() -ne '' } | Select-Object -Last 1).Trim()

if (-not $clientSecret -or $clientSecret.Length -lt 10) {
    Write-Host "❌ ERROR: Could not retrieve client secret from database!" -ForegroundColor Red
    Write-Host "Please enter your client secret manually:" -ForegroundColor Yellow
    $clientSecret = Read-Host "Client Secret"
} else {
    Write-Host "✅ Client secret retrieved (length: $($clientSecret.Length), first 10 chars: $($clientSecret.Substring(0, [Math]::Min(10, $clientSecret.Length)))...)" -ForegroundColor Green
}

# Use the fresh authorization code
$authCode = "1000.05a2dfac87118e1726a1f3a70db0e206.6c2992abd504cddce941953b8330bd24"

$body = @{
    grant_type = "authorization_code"
    client_id = "1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK"
    client_secret = "e27b88023d81a683701e951b9491302bdaa1ebbfca"
    redirect_uri = "http://localhost:8000/oauth/callback"
    code = $authCode
}

Write-Host "Exchanging authorization code for tokens..." -ForegroundColor Green
Write-Host "Code: $authCode" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "https://accounts.zoho.in/oauth/v2/token" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded"
    
    Write-Host "`n=== TOKEN EXCHANGE RESPONSE ===" -ForegroundColor Green
    Write-Host "Response Keys: $($response.PSObject.Properties.Name -join ', ')" -ForegroundColor Yellow
    
    if ($response.refresh_token) {
        Write-Host "`n✅ SUCCESS: refresh_token IS present in Zoho's response!" -ForegroundColor Green
        Write-Host "refresh_token length: $($response.refresh_token.Length)" -ForegroundColor Cyan
        Write-Host "refresh_token (first 50 chars): $($response.refresh_token.Substring(0, [Math]::Min(50, $response.refresh_token.Length)))..." -ForegroundColor Cyan
    } else {
        Write-Host "`n❌ PROBLEM: refresh_token is NOT in Zoho's response!" -ForegroundColor Red
        Write-Host "This means Zoho is not returning it, which could mean:" -ForegroundColor Yellow
        Write-Host "  - The app was already authorized before (Zoho only returns refresh_token on first authorization)" -ForegroundColor Yellow
        Write-Host "  - The access_type=offline parameter isn't working" -ForegroundColor Yellow
        Write-Host "  - OAuth app configuration issue" -ForegroundColor Yellow
    }
    
    Write-Host "`nFull Response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "`n❌ ERROR during token exchange:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Error Details:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}

