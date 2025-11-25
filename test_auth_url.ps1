# Get full authorization URL and test it

Write-Host "Getting authorization URL from backend..." -ForegroundColor Green
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/settings/ticketing-connections/7/oauth/authorize" -Method Get

Write-Host "`nFull Authorization URL:" -ForegroundColor Yellow
$fullUrl = $response.authorization_url
Write-Host $fullUrl -ForegroundColor Cyan

Write-Host "`nChecking URL parameters..." -ForegroundColor Yellow
$uri = [System.Uri]$fullUrl
$queryParams = [System.Web.HttpUtility]::ParseQueryString($uri.Query)

Write-Host "`nURL Parameters:" -ForegroundColor Green
$queryParams.GetEnumerator() | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Cyan
}

# Check if response_type is present
if ($queryParams["response_type"]) {
    Write-Host "`n✅ response_type is present: $($queryParams['response_type'])" -ForegroundColor Green
} else {
    Write-Host "`n❌ PROBLEM: response_type is MISSING from URL!" -ForegroundColor Red
}

# Check if access_type is present
if ($queryParams["access_type"]) {
    Write-Host "✅ access_type is present: $($queryParams['access_type'])" -ForegroundColor Green
} else {
    Write-Host "❌ WARNING: access_type is MISSING from URL!" -ForegroundColor Yellow
}

Write-Host "`nCopy the full URL above and open it in your browser to test." -ForegroundColor Green



