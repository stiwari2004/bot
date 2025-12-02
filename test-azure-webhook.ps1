# Test Azure Monitor Webhook Integration
# This script sends a sample Azure Monitor webhook payload to the local endpoint

$webhookUrl = "http://localhost:8000/api/v1/tickets/webhook/azure_monitor"

Write-Host "Testing Azure Monitor Webhook Integration" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Webhook URL: $webhookUrl" -ForegroundColor Yellow
Write-Host ""

# Sample Azure Monitor webhook payload
$payload = @{
    schemaId = "azureMonitorCommonAlertSchema"
    data = @{
        essentials = @{
            alertId = "12345678-1234-1234-1234-123456789012"
            alertRule = "High CPU Usage"
            severity = "Sev2"
            signalType = "Metric"
            monitorCondition = "Fired"
            monitorService = "Platform"
            targetResource = "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-web-01"
            targetResourceName = "vm-web-01"
            targetResourceGroup = "rg-prod"
            targetResourceType = "Microsoft.Compute/virtualMachines"
            sourceCreatedId = "12345678-1234-1234-1234-123456789012"
            smartGroupId = "12345678-1234-1234-1234-123456789012"
            smartGroupingReason = "Alerts that share the same target resource"
            firedDateTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }
        alertContext = @{
            properties = @{
                key1 = "value1"
                key2 = "value2"
            }
            conditionType = "SingleResourceMultipleMetricCriteria"
            condition = @{
                allOf = @(
                    @{
                        metricName = "Percentage CPU"
                        metricNamespace = "Microsoft.Compute/virtualMachines"
                        operator = "GreaterThan"
                        threshold = "80"
                        timeAggregation = "Average"
                    }
                )
            }
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Sending test payload..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Alert Details:" -ForegroundColor Cyan
Write-Host "  Alert Rule: High CPU Usage" -ForegroundColor White
Write-Host "  Severity: Sev2" -ForegroundColor White
Write-Host "  Monitor Condition: Fired" -ForegroundColor White
Write-Host "  Target Resource: vm-web-01" -ForegroundColor White
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
