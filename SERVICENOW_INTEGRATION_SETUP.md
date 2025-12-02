# ServiceNow Integration Setup Guide

## Overview

The ServiceNow integration provides **two-way communication** between your ServiceNow instance and the bot system:

1. **Inbound (ServiceNow → Bot)**: 
   - API polling to fetch new incidents
   - Webhook receiver for real-time incident updates
   
2. **Outbound (Bot → ServiceNow)**:
   - Status updates when tickets are resolved/closed
   - Comments/work notes added to incidents
   - Automatic incident creation from monitoring alerts

## Features Implemented

✅ **ServiceNow Ticket Fetcher** (`backend/app/services/ticketing_connectors/servicenow.py`)
- OAuth 2.0 authentication
- Basic Auth support
- Fetches incidents from ServiceNow API
- Normalizes ServiceNow incidents to internal ticket format

✅ **Ticketing Poller Integration** (`backend/app/services/ticketing_poller.py`)
- Automatic polling for new ServiceNow incidents
- Configurable sync intervals
- Token refresh handling

✅ **Status Updates** (`backend/app/services/ticketing_integration_service.py`)
- Update incident state (New, In Progress, Resolved, Closed)
- Add work notes/comments to incidents
- Two-way status synchronization

✅ **Webhook Receiver** (`backend/app/api/v1/endpoints/ticket_ingestion.py`)
- Real-time incident ingestion via webhooks
- Supports ServiceNow webhook format

✅ **Ticket Normalizer** (`backend/app/services/ticket/ticket_normalizer.py`)
- Parses ServiceNow incident data
- Maps ServiceNow states/priorities to internal format

## Setup Instructions

### Step 1: Get ServiceNow Instance Details

1. **Instance URL**: Your ServiceNow instance URL (e.g., `https://your-instance.service-now.com`)
2. **Authentication Method**: Choose either:
   - **OAuth 2.0** (Recommended for production)
   - **Basic Auth** (Username/Password - simpler for testing)

### Step 2: OAuth 2.0 Setup (Recommended)

1. **Create OAuth Application in ServiceNow**:
   - Navigate to: `System OAuth > Application Registry`
   - Click "New"
   - Fill in:
     - **Name**: Your app name (e.g., "Bot Integration")
     - **Redirect URL**: `https://your-bot-domain.com/api/v1/auth/callback` (or your callback URL)
     - **Active**: Checked
   - Click "Submit"
   - **Save the Client ID and Client Secret**

2. **Configure OAuth Endpoint**:
   - The OAuth endpoint is: `https://your-instance.service-now.com/oauth_token.do`
   - Grant type: `client_credentials`

### Step 3: Basic Auth Setup (Alternative)

If using Basic Auth:
- **Username**: Your ServiceNow username
- **Password**: Your ServiceNow password
- Note: Basic Auth is simpler but less secure. Use OAuth for production.

### Step 4: Create Connection in Bot System

1. **Via API** (if available):
```json
POST /api/v1/ticketing/connections
{
  "tool_name": "servicenow",
  "connection_type": "api_poll",
  "api_base_url": "https://your-instance.service-now.com",
  "sync_interval_minutes": 5,
  "meta_data": {
    "username": "your-username",  // For Basic Auth
    "password": "your-password",   // For Basic Auth
    // OR for OAuth:
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }
}
```

2. **Via UI** (if available):
   - Navigate to Settings > Ticketing Connections
   - Click "Add Connection"
   - Select "ServiceNow"
   - Enter:
     - Instance URL
     - Authentication method (OAuth or Basic Auth)
     - Credentials
   - Set sync interval (default: 5 minutes)
   - Click "Save"

### Step 5: Configure Webhook (Optional - for Real-time Updates)

1. **In ServiceNow**:
   - Navigate to: `System Web Services > Outbound > REST Messages`
   - Create new REST message:
     - **Name**: Bot Integration Webhook
     - **Endpoint**: `https://your-bot-domain.com/api/v1/tickets/webhook/servicenow`
     - **HTTP Method**: POST
     - **Authentication**: Basic Auth (if required)
   
2. **Create Outbound Notification**:
   - Navigate to: `System Policy > Events > Registry`
   - Find event: `incident.created` or `incident.updated`
   - Add notification to send webhook

3. **Webhook Payload Format**:
   ServiceNow will send incidents in this format:
   ```json
   {
     "result": {
       "sys_id": "abc123",
       "number": "INC0012345",
       "short_description": "High CPU usage",
       "description": "CPU usage is above 80%",
       "state": "1",
       "priority": "2",
       "urgency": "2",
       "impact": "2"
     }
   }
   ```

## Testing the Integration

### Test 1: API Polling

1. Create a test incident in ServiceNow
2. Wait for the sync interval (default: 5 minutes) or trigger manual sync
3. Check the bot system - the incident should appear as a ticket

### Test 2: Webhook Reception

1. Configure webhook in ServiceNow (see Step 5)
2. Create or update an incident in ServiceNow
3. Check bot system logs - you should see webhook received
4. Verify ticket appears in bot system

### Test 3: Status Updates

1. Create a ticket in bot system from a ServiceNow incident
2. Resolve or close the ticket in bot system
3. Check ServiceNow - the incident state should update to "Resolved" (4) or "Closed" (5)
4. Check work notes - comments should be added

### Test 4: OAuth Token Refresh

1. Wait for OAuth token to expire (typically 1 hour)
2. Trigger a sync or status update
3. Check logs - token should be automatically refreshed
4. Verify operations continue to work

## ServiceNow State Mapping

| ServiceNow State | Internal Status | Description |
|-----------------|-----------------|-------------|
| 1 | `open` | New |
| 2 | `in_progress` | In Progress |
| 3 | `open` | On Hold |
| 4 | `resolved` | Resolved |
| 5 | `resolved` | Closed |
| 6 | `resolved` | Canceled |

## ServiceNow Priority Mapping

| ServiceNow Priority | Internal Severity |
|---------------------|-------------------|
| 1 | `critical` |
| 2 | `high` |
| 3 | `medium` |
| 4 | `low` |
| 5 | `low` |

## Monitoring Tools Integration

The ServiceNow integration works with monitoring tools to create incidents automatically:

1. **Monitoring Tool** (e.g., Datadog, Prometheus) detects alert
2. **Bot System** receives alert via webhook
3. **Bot System** creates ServiceNow incident via API
4. **ServiceNow** incident is created and linked to ticket
5. **Bot System** can execute runbooks to resolve the issue
6. **Bot System** updates ServiceNow incident with resolution

## Troubleshooting

### Issue: Authentication Fails

**Symptoms**: 401 Unauthorized errors in logs

**Solutions**:
- Verify credentials are correct
- For OAuth: Check Client ID and Client Secret
- For Basic Auth: Verify username/password
- Check ServiceNow instance URL is correct

### Issue: Incidents Not Appearing

**Symptoms**: No tickets created from ServiceNow incidents

**Solutions**:
- Check poller service is running
- Verify connection is active (`is_active = true`)
- Check sync interval hasn't passed
- Review logs for API errors
- Verify incident state filter (if configured)

### Issue: Status Updates Not Working

**Symptoms**: Bot resolves ticket but ServiceNow incident doesn't update

**Solutions**:
- Verify connection has proper permissions
- Check ServiceNow incident number/sys_id is correct
- Review logs for API errors
- Verify incident isn't in a read-only state

### Issue: OAuth Token Expires

**Symptoms**: Operations work initially but fail after ~1 hour

**Solutions**:
- Token refresh should be automatic
- Check logs for refresh errors
- Verify Client ID/Secret are still valid
- Re-authorize connection if needed

## API Endpoints

### Create Connection
```
POST /api/v1/ticketing/connections
```

### Test Connection
```
POST /api/v1/ticketing/connections/{id}/test
```

### Receive Webhook
```
POST /api/v1/tickets/webhook/servicenow
```

### Manual Sync
```
POST /api/v1/ticketing/connections/{id}/sync
```

## Next Steps

1. **Set up monitoring tool integrations** to automatically create ServiceNow incidents
2. **Configure runbooks** to automatically resolve common issues
3. **Set up alerting** for failed integrations
4. **Monitor integration health** via logs and metrics

## Files Modified/Created

- ✅ `backend/app/services/ticketing_connectors/servicenow.py` (NEW)
- ✅ `backend/app/services/ticketing_poller.py` (UPDATED)
- ✅ `backend/app/services/ticketing_integration_service.py` (UPDATED)
- ✅ `backend/app/services/ticket/ticket_normalizer.py` (UPDATED)
- ✅ `backend/app/api/v1/endpoints/ticket_ingestion.py` (Already supports ServiceNow)

## Support

For issues or questions:
1. Check logs: `backend/logs/audit.log`
2. Review ServiceNow API documentation
3. Test connection via API endpoint
4. Verify credentials and permissions


