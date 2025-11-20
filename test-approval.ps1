# Test Approval Endpoint
# Approves step 1 for session 12

$sessionId = 12
$stepNumber = 1
$baseUrl = "http://localhost:8000"

Write-Host "=== Testing Approval Endpoint ===" -ForegroundColor Cyan
Write-Host "Session ID: $sessionId"
Write-Host "Step Number: $stepNumber"
Write-Host ""

$body = @{
    approve = $true
} | ConvertTo-Json

$url = "$baseUrl/api/v1/agent/$sessionId/approve-step?step_number=$stepNumber"

Write-Host "URL: $url" -ForegroundColor Yellow
Write-Host "Body: $body" -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $url -Method POST -Body $body -ContentType "application/json"
    Write-Host "Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 5)
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Check Backend Logs ===" -ForegroundColor Cyan
Write-Host "Run: docker-compose logs backend --tail 50 | Select-String -Pattern 'APPROVE_STEP|EXECUTE_STEP'"




