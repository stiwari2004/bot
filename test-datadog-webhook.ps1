# Test Datadog Webhook Integration
# This script sends a sample Datadog webhook payload to the local endpoint

$webhookUrl = "http://localhost:8000/api/v1/tickets/webhook/datadog"

Write-Host "Testing Datadog Webhook Integration" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Yellow
Write-Host ""

# Sample Datadog webhook payload
$payload = @{
    title = "High CPU Usage on Production Server"
    text = "CPU usage has exceeded 90% for the past 5 minutes on server prod-web-01"
    alert_id = "123456789"
    alert_metric = "system.cpu.usage"
    alert_status = "alerting"
    alert_transition = "Triggered"
    priority = "high"
    tags = @("env:prod", "service:web", "team:platform")
    event_type = "alert"
    date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json -Depth 10

Write-Host "Sending test payload..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Alert Details:" -ForegroundColor Cyan
Write-Host "  Alert Title: High CPU Usage on Production Server" -ForegroundColor White
Write-Host "  Priority: high" -ForegroundColor White
Write-Host "  Status: alerting" -ForegroundColor White
Write-Host "  Tags: env:prod, service:web, team:platform" -ForegroundColor White
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


