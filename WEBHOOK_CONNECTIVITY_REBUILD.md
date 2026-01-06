# Webhook Connectivity Rebuild - Summary

## Overview
Rebuilt webhook connectivity for SolarWinds, Datadog, and other monitoring tools. The system now automatically generates webhook URLs and provides proper endpoints for receiving alerts.

## Changes Made

### 1. Automatic Webhook URL Generation
- **File**: `backend/app/api/v1/endpoints/monitoring_connections.py`
- **Feature**: When creating a webhook connection, the system automatically generates the webhook URL if not provided
- **URL Format**: `{BACKEND_BASE_URL}/api/v1/alerts/webhook/{tool_name}`
- **Example**: `http://localhost:8000/api/v1/alerts/webhook/solarwinds`

### 2. New Webhook Endpoint in Alerts Router
- **File**: `backend/app/api/v1/endpoints/alerts.py`
- **Endpoint**: `POST /api/v1/alerts/webhook/{source}`
- **Purpose**: Better organization - alerts are received in the alerts router
- **Backward Compatibility**: The old endpoint `/api/v1/tickets/webhook/{source}` still works

### 3. Enhanced Monitoring Connections API
- **Auto-generates webhook URLs**: When creating a webhook connection, the URL is automatically generated
- **Test connection improvements**: Webhook connections now return the generated URL in the test response
- **Better error handling**: Improved error messages and logging

## Supported Monitoring Tools

### SolarWinds ✅
- **Webhook URL**: `/api/v1/alerts/webhook/solarwinds`
- **Normalization**: Uses `SolarWindsConnector.normalize_webhook()`
- **Status Mapping**:
  - `triggered`, `active`, `firing` → `firing`
  - `resolved`, `ok` → `resolved`
- **Connection Types**: Both `webhook` and `api` supported

### Datadog ✅
- **Webhook URL**: `/api/v1/alerts/webhook/datadog`
- **Normalization**: Uses `DatadogConnector.normalize_webhook()`
- **Status Mapping**:
  - `alerting` → `firing`
  - `resolved`, `ok`, `ok_no_data` → `resolved`
- **Connection Types**: Both `webhook` and `api` supported

### Other Tools
- **Prometheus**: `/api/v1/alerts/webhook/prometheus`
- **Azure Monitor**: `/api/v1/alerts/webhook/azure_monitor`
- **Splunk**: `/api/v1/alerts/webhook/splunk`

## API Endpoints

### Create Monitoring Connection
```http
POST /api/v1/connectors/monitoring-connections
Content-Type: application/json
Authorization: Bearer {token}

{
  "tool_name": "solarwinds",
  "connection_type": "webhook",
  "api_base_url": "https://api.us-1.cloud.solarwinds.com",  // Optional for webhook
  "api_key": "your-api-key",  // Optional for webhook
  "is_active": true
}
```

**Response**:
```json
{
  "id": 1,
  "tool_name": "solarwinds",
  "connection_type": "webhook",
  "is_active": true,
  "webhook_url": "http://localhost:8000/api/v1/alerts/webhook/solarwinds",
  "api_base_url": "https://api.us-1.cloud.solarwinds.com",
  "message": "Monitoring tool connection created successfully"
}
```

### Test Connection
```http
POST /api/v1/connectors/monitoring-connections/{connection_id}/test
Authorization: Bearer {token}
```

**For Webhook Connections**:
```json
{
  "success": true,
  "message": "Webhook connection configured. Use this URL in solarwinds: http://localhost:8000/api/v1/alerts/webhook/solarwinds",
  "webhook_url": "http://localhost:8000/api/v1/alerts/webhook/solarwinds"
}
```

**For API Connections**:
```json
{
  "success": true,
  "message": "Connection successful. Found 10 available metrics."
}
```

### List Connections
```http
GET /api/v1/connectors/monitoring-connections
Authorization: Bearer {token}
```

**Response**:
```json
{
  "connections": [
    {
      "id": 1,
      "tool_name": "solarwinds",
      "connection_type": "webhook",
      "is_active": true,
      "webhook_url": "http://localhost:8000/api/v1/alerts/webhook/solarwinds",
      "api_base_url": null,
      "last_sync_at": null,
      "last_sync_status": null,
      "last_error": null,
      "meta_data": null
    }
  ]
}
```

## Webhook Endpoints

### Primary Endpoint (Recommended)
```http
POST /api/v1/alerts/webhook/{source}
Content-Type: application/json

{
  "alert_id": "12345",
  "alert_name": "High CPU Usage",
  "alert_status": "triggered",
  "severity": "critical",
  ...
}
```

### Legacy Endpoint (Backward Compatible)
```http
POST /api/v1/tickets/webhook/{source}
Content-Type: application/json

{
  "alert_id": "12345",
  "alert_name": "High CPU Usage",
  "alert_status": "triggered",
  "severity": "critical",
  ...
}
```

Both endpoints create **ALERTS** (not tickets) in the alerts table.

## Configuration

### Environment Variables
- `BACKEND_BASE_URL`: Base URL for the backend API (default: `http://localhost:8000`)
  - Used to generate webhook URLs automatically
  - Example: `BACKEND_BASE_URL=https://api.yourdomain.com`

### Database
- **Table**: `monitoring_tool_connections`
- **Fields**:
  - `tool_name`: Name of the monitoring tool
  - `connection_type`: `webhook` or `api`
  - `webhook_url`: Auto-generated URL for webhook connections
  - `api_base_url`: API base URL for API connections
  - `api_key`: API key (encrypted)
  - `tenant_id`: Tenant ID for multi-tenant support

## Tenant Resolution

When a webhook is received:
1. System looks up the monitoring connection by `tool_name` and `connection_type=webhook`
2. Uses the `tenant_id` from the connection
3. Falls back to `tenant_id=1` (demo) if no connection found

## Testing

### Test Webhook Connection
1. Create a webhook connection via API or UI
2. The system automatically generates the webhook URL
3. Use the generated URL in your monitoring tool's webhook configuration
4. Test the connection using the test endpoint

### Test Webhook Reception
```bash
# Test SolarWinds webhook
curl -X POST http://localhost:8000/api/v1/alerts/webhook/solarwinds \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "12345",
    "alert_name": "Test Alert",
    "alert_status": "triggered",
    "severity": "critical",
    "entity_name": "server-01"
  }'
```

## Troubleshooting

### "Failed to fetch monitoring connections"
- **Cause**: Endpoint not registered or authentication issue
- **Fix**: Ensure the monitoring_connections router is included in `api.py`
- **Check**: Verify `GET /api/v1/connectors/monitoring-connections` returns 200

### Webhook URL not generated
- **Cause**: `BACKEND_BASE_URL` not set or connection type not "webhook"
- **Fix**: Set `BACKEND_BASE_URL` environment variable
- **Check**: Verify connection type is "webhook" when creating

### Webhook not received
- **Cause**: Monitoring tool not configured with correct URL
- **Fix**: Copy the generated webhook URL from the connection test response
- **Check**: Verify the URL is accessible from the monitoring tool's network

### Tenant not found
- **Cause**: No active webhook connection for the source
- **Fix**: Create a webhook connection for the monitoring tool
- **Note**: System falls back to tenant_id=1 (demo) if no connection found

## Next Steps

1. ✅ Webhook URL auto-generation
2. ✅ Webhook endpoint in alerts router
3. ✅ Backward compatibility maintained
4. ✅ SolarWinds and Datadog normalization working
5. ⏳ Update frontend to display generated webhook URLs
6. ⏳ Add webhook URL copy-to-clipboard functionality
7. ⏳ Add webhook test payload generator in UI

## Files Modified

1. `backend/app/api/v1/endpoints/monitoring_connections.py`
   - Added `generate_webhook_url()` function
   - Auto-generate webhook URLs on creation
   - Enhanced test connection response

2. `backend/app/api/v1/endpoints/alerts.py`
   - Added webhook endpoint `/webhook/{source}`
   - Tenant resolution from monitoring connections
   - Proper error handling

3. `backend/app/core/config.py`
   - Uses `BACKEND_BASE_URL` for webhook URL generation

## Architecture

```
Monitoring Tool (SolarWinds/Datadog)
    ↓
POST /api/v1/alerts/webhook/{source}
    ↓
AlertController.receive_webhook()
    ↓
TicketNormalizer.normalize()
    ↓
Connector.normalize_webhook() (SolarWinds/Datadog)
    ↓
Alert stored in alerts table
```

## Status

✅ **All tasks completed**
- Monitoring connections API working
- Webhook URL auto-generation implemented
- Webhook endpoints available
- SolarWinds and Datadog normalization working
- Backward compatibility maintained

