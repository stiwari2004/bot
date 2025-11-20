# Test Azure Connection Endpoint
param(
    [Parameter(Mandatory=$true)]
    [int]$ConnectionId
)

Write-Host "=== Testing Azure Connection ===" -ForegroundColor Cyan
Write-Host "Connection ID: $ConnectionId" -ForegroundColor Yellow

# Test endpoint
$testUrl = "http://localhost:8000/api/v1/connectors/infrastructure-connections/$ConnectionId/test"
Write-Host "`n1. Testing connection..." -ForegroundColor Yellow
Write-Host "   URL: $testUrl" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri $testUrl -Method POST -ContentType "application/json" -ErrorAction Stop
    Write-Host "   ✓ Test successful!" -ForegroundColor Green
    Write-Host "   Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 5 | Write-Host
} catch {
    Write-Host "   ✗ Test failed!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Discover endpoint
$discoverUrl = "http://localhost:8000/api/v1/connectors/infrastructure-connections/$ConnectionId/discover"
Write-Host "`n2. Discovering resources..." -ForegroundColor Yellow
Write-Host "   URL: $discoverUrl" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri $discoverUrl -Method GET -ErrorAction Stop
    Write-Host "   ✓ Discovery successful!" -ForegroundColor Green
    Write-Host "   Found $($response.total) resources" -ForegroundColor Cyan
    if ($response.resources -and $response.resources.Count -gt 0) {
        Write-Host "   Resources:" -ForegroundColor Cyan
        foreach ($vm in $response.resources) {
            Write-Host "     - $($vm.name) (RG: $($vm.resource_group))" -ForegroundColor White
        }
    } else {
        Write-Host "   ⚠ No resources found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Discovery failed!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan





