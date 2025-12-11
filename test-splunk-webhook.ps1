# Test Splunk Webhook Integration
# This script sends a sample Splunk webhook payload to the local endpoint

$webhookUrl = "http://localhost:8000/api/v1/tickets/webhook/splunk"

Write-Host "Testing Splunk Webhook Integration" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Yellow
Write-Host ""

# Sample Splunk webhook payload (HTTP Event Collector format)
$payload = @{
    time = [Math]::Floor((Get-Date).ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalSeconds)
    host = "splunk-server-01"
    source = "splunk_alert"
    sourcetype = "alert"
    event = @{
        alert_name = "High Error Rate Detected"
        alert_message = "Error rate has exceeded 5% for the past 10 minutes"
        severity = "high"
        status = "firing"
        search_name = "Error Rate Monitor"
        search_id = "1234567890"
        results_link = "https://splunk.example.com/app/search/search?q=search%20error"
        environment = "prod"
        service = "api"
        tags = @("error", "monitoring", "alert")
    }
} | ConvertTo-Json -Depth 10

Write-Host "Sending test payload..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Alert Details:" -ForegroundColor Cyan
Write-Host "  Alert Name: High Error Rate Detected" -ForegroundColor White
Write-Host "  Severity: high" -ForegroundColor White
Write-Host "  Status: firing" -ForegroundColor White
Write-Host "  Environment: prod" -ForegroundColor White
Write-Host "  Service: api" -ForegroundColor White
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $payload -ContentType "application/json" -ErrorAction Stop
    
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 5 | Write-Host -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Check backend logs: docker-compose logs -f backend" -ForegroundColor White
    Write-Host "2. Check alerts: GET http://localhost:8000/api/v1/alerts/alerts" -ForegroundColor White
    Write-Host "3. View in UI: http://localhost:3000 (Alerts section)" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: This creates an ALERT, not a ticket." -ForegroundColor Gray
    Write-Host "Tickets come from ticketing tools (ServiceNow/ManageEngine) via polling." -ForegroundColor Gray
    Write-Host "Alerts are used for validation and matching with tickets." -ForegroundColor Gray
} catch {
    Write-Host "❌ ERROR!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error Details:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Ensure backend is running: docker-compose ps" -ForegroundColor White
    Write-Host "2. Check backend logs: docker-compose logs backend" -ForegroundColor White
    Write-Host "3. Verify webhook endpoint is accessible: curl $webhookUrl" -ForegroundColor White
}









