# Monitoring Tools Webhook Setup

## ✅ Completed Setup

All monitoring tools are configured to create **ALERTS** (not tickets) when webhooks are received.

### Architecture

```
Monitoring Tools → Webhooks → Alerts (in alerts table)
Ticketing Tools → Polling → Tickets (in tickets table)
```

## Supported Monitoring Tools

### 1. Prometheus Alertmanager ✅
- **Webhook URL**: `POST /api/v1/tickets/webhook/prometheus`
- **Test Script**: `test-prometheus-webhook.ps1`
- **Status**: Working and tested
- **Status Mapping**: 
  - `firing` → `firing`
  - `resolved` → `resolved`

### 2. Datadog ✅
- **Webhook URL**: `POST /api/v1/tickets/webhook/datadog`
- **Test Script**: `test-datadog-webhook.ps1`
- **Status**: Working and tested
- **Status Mapping**:
  - `alerting` → `firing`
  - `resolved`, `ok`, `ok_no_data` → `resolved`

### 3. Azure Monitor ⏳
- **Webhook URL**: `POST /api/v1/tickets/webhook/azure_monitor`
- **Test Script**: `test-azure-webhook.ps1`
- **Status**: Ready to test
- **Status Mapping**:
  - `Fired` → `firing`
  - `Resolved` → `resolved`

### 4. Splunk ⏳
- **Webhook URL**: `POST /api/v1/tickets/webhook/splunk`
- **Test Script**: `test-splunk-webhook.ps1`
- **Status**: Ready to test
- **Status Mapping**: Defaults to `firing`

## Testing

### Test All Webhooks

```powershell
# Test Prometheus
.\test-prometheus-webhook.ps1

# Test Datadog
.\test-datadog-webhook.ps1

# Test Azure Monitor
.\test-azure-webhook.ps1

# Test Splunk
.\test-splunk-webhook.ps1
```

### View Alerts in UI

1. Open `http://localhost:3000`
2. Click **"Alerts"** in the sidebar (under "Agent Tools")
3. View all alerts from monitoring tools
4. Filter by status, severity, or source
5. Click an alert to see full details

### View Alerts via API

```bash
# List all alerts
GET http://localhost:8000/api/v1/alerts/alerts

# Filter by status
GET http://localhost:8000/api/v1/alerts/alerts?status=firing

# Filter by source
GET http://localhost:8000/api/v1/alerts/alerts?source=prometheus

# Get alert details
GET http://localhost:8000/api/v1/alerts/alerts/{alert_id}
```

## Alert Status Values

- **firing**: Alert is active and needs attention
- **resolved**: Alert has been resolved/cleared
- **acknowledged**: Alert has been acknowledged (future feature)

## Alert Severity Values

- **critical**: Critical issue requiring immediate attention
- **high**: High priority issue
- **medium**: Medium priority issue
- **low**: Low priority issue

## Next Steps

1. ✅ Test all monitoring tools
2. ⏳ Implement alert closing/updating functionality
3. ⏳ Add alert matching with tickets
4. ⏳ Create scenario testing framework
5. ⏳ Plan next development moves

## Configuration

### Webhook Endpoints

All webhooks are received at:
```
POST /api/v1/tickets/webhook/{source}
```

Where `{source}` is one of:
- `prometheus`
- `datadog`
- `azure_monitor`
- `splunk`

### Payload Format

Each monitoring tool has its own payload format, which is normalized by the respective connector:
- `backend/app/services/monitoring_connectors/prometheus.py`
- `backend/app/services/monitoring_connectors/datadog.py`
- `backend/app/services/monitoring_connectors/azure_monitor.py`
- `backend/app/services/monitoring_connectors/splunk.py`

The normalized format is:
```json
{
  "external_id": "alert-id",
  "title": "Alert Title",
  "description": "Alert Description",
  "severity": "critical|high|medium|low",
  "environment": "prod|staging|dev",
  "service": "service-name",
  "metadata": {
    // Tool-specific metadata
  }
}
```

## Troubleshooting

### Alerts Not Appearing

1. Check backend logs:
   ```bash
   docker-compose logs -f backend
   ```

2. Verify webhook endpoint is accessible:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tickets/webhook/prometheus \
     -H "Content-Type: application/json" \
     -d @prometheus_test_payload.json
   ```

3. Check alerts API:
   ```bash
   curl http://localhost:8000/api/v1/alerts/alerts
   ```

### Alert Status Not Correct

- Check the connector's `normalize_webhook` method
- Verify status mapping in `AlertController.receive_webhook`
- Check backend logs for normalization errors

## Notes

- **Alerts are NOT tickets**: Alerts come from monitoring tools, tickets come from ticketing tools
- **No ticket creation**: Webhooks create alerts only, not tickets
- **Single pane of glass**: View both alerts and tickets in the UI
- **Future matching**: Alerts can be matched with tickets for validation


