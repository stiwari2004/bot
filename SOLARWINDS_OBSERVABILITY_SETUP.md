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

SolarWinds Observability SaaS uses REST API v1. Common endpoints:

- **Metrics**: `GET /v1/metrics`
- **Measurements**: `POST /v1/measurements`
- **Events**: `GET /v1/events` (if available)
- **Alerts**: `GET /v1/alerts` (if available - varies by product)

**Important**: Not all Observability SaaS products expose alerts through the API. The exact endpoints depend on your specific product (AppOptics, Loggly, Papertrail, etc.).

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

## Next Steps

Once connected, your application will:
- Fetch alerts from SolarWinds Observability
- Sync alert statuses (acknowledge/resolve)
- Display monitoring data in your dashboard

For more information, see the [SolarWinds Observability API Documentation](https://documentation.solarwinds.com/en/success_center/observability/content/api/api.htm).

