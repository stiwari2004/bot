# SolarWinds Observability SaaS Setup Guide

This guide explains how to connect your application to **SolarWinds Observability SaaS** (formerly AppOptics, Loggly, Papertrail).

## Prerequisites

- Access to your SolarWinds Observability SaaS account
- Admin or API token creation permissions

## Step 1: Get Your Data Center Identifier

1. Log in to your SolarWinds Observability account
2. Check the URL in your browser - it will look like: `https://app.xx-yy.cloud.solarwinds.com`
   - The `xx-yy` part is your **data center identifier**
   - Example: If your URL is `https://app.us-1.cloud.solarwinds.com`, your data center is `us-1`

## Step 2: Generate an API Token

1. **Navigate to API Tokens**:
   - Log in to SolarWinds Observability
   - Go to **Settings** → **API Tokens**
   - Or directly: `https://app.xx-yy.cloud.solarwinds.com/settings/api-tokens`

2. **Create New Token**:
   - Click **"Generate New API Token"** or **"Create Token"**
   - Enter a descriptive name (e.g., "Resolvify Bot Integration")
   - Select the appropriate role:
     - **Full Access**: Complete access (use for integrations that need to create/modify resources)
     - **Record Only**: For agents/collectors to record metrics (read/write metrics)
     - **View Only**: Read-only access (for monitoring/alerting only)
   - Click **"Save"** or **"Create"**

3. **Copy the Token**:
   - ⚠️ **IMPORTANT**: Copy the token immediately - you won't be able to view it again!
   - Store it securely (password manager, secret management tool)
   - If you lose it, you'll need to generate a new one

## Step 3: Configure Connection in Your Application

### Option A: Via UI (Recommended)

1. Navigate to **Settings** → **Monitoring Connections** in your application
2. Click **"Add Connection"**
3. Select **"SolarWinds"** from the dropdown
4. Fill in the connection details:

   **API Base URL**:
   ```
   https://api.xx-yy.cloud.solarwinds.com
   ```
   Replace `xx-yy` with your data center identifier (e.g., `us-1`, `eu-1`)

   **Authentication Method**: Select **"API Key"**

   **API Key**: Paste the token you generated in Step 2

5. Click **"Test Connection"** to verify
6. Click **"Save"**

### Option B: Via API

```bash
POST /api/v1/connectors/monitoring-connections
Content-Type: application/json
Authorization: Bearer YOUR_APP_TOKEN

{
  "tool_name": "solarwinds",
  "connection_type": "api",
  "api_base_url": "https://api.xx-yy.cloud.solarwinds.com",
  "api_key": "YOUR_SOLARWINDS_API_TOKEN",
  "sync_interval_minutes": 5
}
```

## Step 4: Verify Connection

After creating the connection:

1. Click **"Test Connection"** in the UI, or
2. Use the API:
   ```bash
   POST /api/v1/connectors/monitoring-connections/{connection_id}/test
   ```

You should see a success message if the connection is working.

## API Endpoints Reference

SolarWinds Observability SaaS uses REST API v1. Available endpoints typically include:

- **Metrics**: `GET /v1/metrics` - List available metrics
- **Measurements**: `POST /v1/measurements` - Submit metric measurements
- **Entities**: `GET /v1/entities` - List monitored entities
- **Change Events**: `GET /v1/changeEvents` - Infrastructure change events
- **Logs**: `GET /v1/logs` - Log entries
- **Metadata**: `GET /v1/metadata` - Entity metadata
- **Cloud Accounts**: `GET /v1/cloudAccounts` - Cloud account information
- **DBO**: `GET /v1/dbo` - Database observability data
- **DEM**: `GET /v1/dem` - Digital experience monitoring data
- **Tokens**: `GET /v1/tokens` - API token management

### ⚠️ Important: No Direct Alerts Endpoint

**SolarWinds Observability SaaS does NOT have a direct `/v1/alerts` endpoint.**

Alerts in Observability SaaS are typically:
1. **Webhook-based**: Configure webhooks in the UI to receive alerts
2. **Metric-derived**: Alerts are created from metric thresholds in the UI
3. **Change Events**: Infrastructure changes via `/v1/changeEvents`
4. **UI-managed**: Alerts are primarily managed through the dashboard

### View Available Endpoints

To see all available endpoints for your data center, visit the Swagger UI:
```
https://api.ap-01.cloud.solarwinds.com/v1/#/
```
(Replace `ap-01` with your data center identifier)

The Swagger UI shows:
- All available endpoints
- Required parameters
- Request/response formats
- A playground to test endpoints

### Alternative: Webhook Integration

For real-time alerts, configure webhooks in SolarWinds Observability:
1. Go to Settings → Integrations → Webhooks
2. Create a webhook pointing to your application's webhook endpoint
3. Configure alert conditions in the UI
4. Alerts will be sent to your webhook when conditions are met

Full API documentation: https://documentation.solarwinds.com/en/success_center/observability/content/api/api-swagger.htm

## Data Center Identifiers

Common data center identifiers:
- `us-1`: United States (East)
- `us-2`: United States (West)
- `eu-1`: Europe
- `ap-1`: Asia Pacific

Find your exact identifier in your account URL or contact SolarWinds support.

## Security Best Practices

1. **Token Security**:
   - Never commit API tokens to version control
   - Use environment variables or secret management tools
   - Rotate tokens regularly (every 90 days recommended)

2. **Principle of Least Privilege**:
   - Use the minimum role required for your integration
   - For read-only monitoring, use "View Only"
   - For metric collection, use "Record Only"

3. **Token Rotation**:
   - If a token is compromised, revoke it immediately
   - Generate a new token and update your connection
   - Old tokens cannot be recovered

## Troubleshooting

### "401 Unauthorized" Error
- Verify your API token is correct
- Check that the token hasn't been revoked
- Ensure you're using the correct data center identifier

### "404 Not Found" Error
- Verify the API base URL format: `https://api.xx-yy.cloud.solarwinds.com`
- Check that your data center identifier is correct

### "403 Forbidden" Error
- Your token may not have sufficient permissions
- Generate a new token with "Full Access" role
- Verify the token hasn't expired

### Connection Test Fails
- Check network connectivity to `api.xx-yy.cloud.solarwinds.com`
- Verify firewall rules allow outbound HTTPS (port 443)
- Check if your organization has IP whitelisting enabled

## ⚠️ Important: Alerts via Webhooks (Like Datadog)

**SolarWinds Observability SaaS uses webhooks for alerts, similar to Datadog.**

Just like Datadog:
- **Webhooks**: Real-time alert notifications (push-based)
- **API**: For connection testing and status updates (not for fetching alerts)

**Available API endpoints**: changeEvents, cloudAccounts, dbo, dem, entities, logs, metadata, metrics, tokens

**Note**: There is no `/v1/alerts` endpoint for polling alerts. Alerts are:
1. **Webhook-based**: Configure webhooks in the UI to receive alerts (recommended)
2. **Metric-derived**: Alerts are created from metric thresholds in the UI
3. **Change Events**: Infrastructure changes via `/v1/changeEvents` (for infrastructure monitoring)
4. **UI-managed**: Alerts are primarily managed through the dashboard

## Step 4: Set Up Webhooks for Alerts (Required)

**SolarWinds Observability SaaS uses webhooks for alerts, just like Datadog.**

### Configure Webhook in SolarWinds Observability UI

1. **Navigate to Webhooks**:
   - Go to **Settings** → **Integrations** → **Webhooks**
   - Or directly: `https://app.xx-yy.cloud.solarwinds.com/settings/integrations/webhooks`

2. **Create New Webhook**:
   - Click **"Create Webhook"** or **"Add Webhook"**
   - Enter a name (e.g., "Resolvify Bot Alerts")
   - Set the webhook URL:
     ```
     https://your-domain.com/api/v1/alerts/webhook/solarwinds
     ```
     (Replace `your-domain.com` with your actual domain)

3. **Configure Alert Conditions**:
   - Set up metric thresholds, entity health checks, or log-based alerts
   - When conditions are met, SolarWinds will POST alert data to your webhook
   - The webhook payload will be automatically normalized and stored as an alert

4. **Test the Webhook**:
   - Use the "Test" button in SolarWinds UI
   - Or trigger a test alert condition
   - Check your application logs to verify the webhook is received

### Webhook Payload Format

Your application expects webhook payloads in this format (SolarWinds will send similar data):

```json
{
  "alert_id": "12345",
  "alert_name": "High CPU Usage",
  "alert_message": "CPU usage exceeded threshold",
  "alert_status": "triggered",
  "severity": "critical",
  "entity_name": "server-01",
  "metric_name": "cpu.usage",
  "metric_value": 95.5,
  "threshold": 90.0,
  "timestamp": "2025-01-01T00:00:00Z",
  "tags": ["env:prod", "service:api"]
}
```

**Note**: The exact payload format may vary based on your SolarWinds configuration. The connector will normalize it automatically.

## Integration Status

- ✅ **Connection Test**: Works (uses `/v1/metrics`)
- ✅ **Authentication**: Working
- ✅ **Webhooks**: Supported (configure in SolarWinds UI)
- ✅ **Alert Updates**: API supports acknowledge/resolve operations
- ✅ **Metrics**: Available via `/v1/metrics`
- ✅ **Change Events**: Available via `/v1/changeEvents` (for infrastructure monitoring)

## Alternative: Poll Change Events (Optional)

If you want to monitor infrastructure changes (not alerts), you can poll the changeEvents endpoint:

```bash
curl -X 'GET' \
  'https://api.ap-01.cloud.solarwinds.com/v1/changeEvents' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

This is useful for tracking infrastructure changes, but **not for alerts**. Use webhooks for alerts.

For more information, see the [SolarWinds Observability API Documentation](https://documentation.solarwinds.com/en/success_center/observability/content/api/api-swagger.htm).

