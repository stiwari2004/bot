# Quick Guide: Test ServiceNow Connection

## Step 0: Check Existing Connections

First, check if a connection already exists (from UI or previous attempts):

```powershell
.\check-servicenow-connection-simple.ps1
```

This will show:
- If a connection exists
- Connection details (ID, status, last sync)
- Authentication method used

## Option 1: Using PowerShell Script (Easiest)

### Step 1: Create Connection

**Interactive Mode (Recommended - Prompts for credentials):**
```powershell
.\create-servicenow-connection.ps1 -InstanceUrl "https://your-instance.service-now.com"
```
The script will then prompt you to:
1. Choose authentication method (Basic Auth or OAuth)
2. Enter credentials securely

**For Basic Auth (with parameters):**
```powershell
.\create-servicenow-connection.ps1 `
    -InstanceUrl "https://your-instance.service-now.com" `
    -Username "your-username" `
    -Password "your-password" `
    -SyncIntervalMinutes 5
```

**For OAuth 2.0:**
```powershell
.\create-servicenow-connection.ps1 `
    -InstanceUrl "https://your-instance.service-now.com" `
    -ClientId "your-client-id" `
    -ClientSecret "your-client-secret" `
    -SyncIntervalMinutes 5
```

### Step 2: Test Connection

**Using PowerShell (Recommended - No Python dependencies needed):**
```powershell
.\test-servicenow-connection-api.ps1
```

**Or using Python (requires backend environment):**
```powershell
cd backend
python ..\test-servicenow-connection.py
```

## Option 2: Using API Directly

### Step 1: Create Connection

**For Basic Auth:**
```bash
curl -X POST "http://localhost:8000/api/v1/ticketing-connections" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "servicenow",
    "connection_type": "api_poll",
    "api_base_url": "https://your-instance.service-now.com",
    "sync_interval_minutes": 5,
    "meta_data": {
      "username": "your-username",
      "password": "your-password"
    }
  }'
```

**For OAuth 2.0:**
```bash
curl -X POST "http://localhost:8000/api/v1/ticketing-connections" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "servicenow",
    "connection_type": "api_poll",
    "api_base_url": "https://your-instance.service-now.com",
    "sync_interval_minutes": 5,
    "meta_data": {
      "client_id": "your-client-id",
      "client_secret": "your-client-secret"
    }
  }'
```

### Step 2: Test Connection

Replace `{connection_id}` with the ID returned from Step 1:

```bash
curl -X POST "http://localhost:8000/api/v1/ticketing-connections/{connection_id}/test"
```

## Option 3: Using Python Script

### Step 1: Create Connection (via API or UI)

### Step 2: Test Connection

```bash
python test-servicenow-connection.py
```

## Expected Results

### ✅ Success
```
✅ Successfully fetched X incidents

Sample incidents:
1. Incident Title
   Number: INC0012345
   Status: open
   Severity: high
   ServiceNow State: 1
```

### ❌ Common Errors

**401 Unauthorized:**
- Check username/password or OAuth credentials
- Verify credentials are correct in ServiceNow

**404 Not Found:**
- Check ServiceNow instance URL is correct
- Ensure instance is accessible

**403 Forbidden:**
- User doesn't have permissions to read incidents
- Check ServiceNow user roles

**Connection Timeout:**
- ServiceNow instance not accessible from server
- Check network/firewall settings

## What Gets Tested

1. **Authentication**: Verifies credentials work
2. **API Access**: Tests ability to query ServiceNow API
3. **Data Fetching**: Actually fetches incidents to verify connection
4. **Token Refresh**: For OAuth, tests token refresh if needed

## Next Steps After Successful Test

1. ✅ Connection is working
2. Enable automatic polling (connection is already active)
3. Test webhook reception (optional)
4. Test status updates (resolve a ticket and check ServiceNow)

