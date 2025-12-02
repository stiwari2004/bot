# Test Prometheus Alertmanager Webhook Integration
# This script sends a test payload to the Prometheus webhook endpoint

$webhookUrl = "http://localhost:8000/api/v1/tickets/webhook/prometheus"

# Test payload - Prometheus Alertmanager webhook format
$testPayload = @{
    version = "4"
    groupKey = "{}:{alertname=`"HighCPUUsage`"}"
    status = "firing"
    receiver = "troubleshooting-ai-webhook"
    groupLabels = @{
        alertname = "HighCPUUsage"
    }
    commonLabels = @{
        alertname = "HighCPUUsage"
        severity = "warning"
        instance = "server1:9100"
        job = "node_exporter"
        environment = "prod"
        service = "web-server"
    }
    commonAnnotations = @{
        description = "CPU usage is above 80% on server1:9100"
        summary = "High CPU usage detected"
    }
    externalURL = "http://alertmanager:9093"
    alerts = @(
        @{
            status = "firing"
            labels = @{
                alertname = "HighCPUUsage"
                severity = "warning"
                instance = "server1:9100"
                job = "node_exporter"
                environment = "prod"
                service = "web-server"
            }
            annotations = @{
                description = "CPU usage is above 80% on server1:9100"
                summary = "High CPU usage detected"
            }
            startsAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            endsAt = "0001-01-01T00:00:00Z"
            generatorURL = "http://prometheus:9090/graph?g0.expr=cpu_usage%20%3E%2080"
            fingerprint = "abc123def456$(Get-Date -Format 'yyyyMMddHHmmss')"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Testing Prometheus Alertmanager Webhook Integration" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Sending test payload..." -ForegroundColor White
Write-Host ""
Write-Host "Alert Details:" -ForegroundColor Cyan
Write-Host "  Alert Name: HighCPUUsage" -ForegroundColor White
Write-Host "  Severity: warning" -ForegroundColor White
Write-Host "  Instance: server1:9100" -ForegroundColor White
Write-Host "  Status: firing" -ForegroundColor White
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $testPayload -ContentType "application/json"
    
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 5 | Write-Host
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Check backend logs: docker-compose logs -f backend" -ForegroundColor White
    Write-Host "2. Check alerts: GET http://localhost:8000/api/v1/alerts/alerts" -ForegroundColor White
    Write-Host "3. View in UI: http://localhost:3000 (Alerts section - coming soon)" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: This creates an ALERT, not a ticket." -ForegroundColor Gray
    Write-Host "Tickets come from ticketing tools (ServiceNow/ManageEngine) via polling." -ForegroundColor Gray
    Write-Host "Alerts are used for validation and matching with tickets." -ForegroundColor Gray
    
} catch {
    Write-Host "❌ ERROR!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response body: $responseBody" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Ensure backend is running: docker-compose ps" -ForegroundColor White
    Write-Host "2. Check backend logs: docker-compose logs backend" -ForegroundColor White
    Write-Host "3. Verify webhook URL is correct" -ForegroundColor White
}

