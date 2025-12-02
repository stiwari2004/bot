# Quick Start: ServiceNow Integration

## 🎯 Goal
Set up ServiceNow integration with a proper service account (not admin credentials).

## 📋 Step-by-Step Guide

### Step 1: Create ServiceNow Service Account (5 minutes)

**Why?** Security best practice - don't use admin credentials for integrations.

1. **In ServiceNow**, go to: `System Security > Users > Users`
2. **Click "New"** and create:
   - **User ID**: `bot-integration` (or your preferred name)
   - **First Name**: `Bot`
   - **Last Name**: `Integration`
   - **Email**: `bot-integration@yourcompany.com`
   - **Active**: ✅ Checked
   - **Password**: Set a strong password (save it!)
   - **Password Needs Reset**: ❌ Unchecked
3. **Click "Submit"**
4. **Go to "Roles" tab** and add:
   - `itil`
   - `sn_incident_read`
   - `sn_incident_write`
   - `rest_api_explorer`
5. **Click "Save"**

📖 **Full guide**: See `SERVICENOW_SERVICE_ACCOUNT_SETUP.md` for detailed instructions

### Step 2: Check if Connection Already Exists

```powershell
.\check-servicenow-connection-simple.ps1
```

If you see a connection, you can skip to Step 4.

### Step 3: Create Connection (Interactive)

```powershell
.\create-servicenow-connection.ps1 -InstanceUrl "https://dev229095.service-now.com"
```

The script will:
1. Ask for authentication method (1 = Basic Auth, 2 = OAuth)
2. Prompt for credentials securely
3. Create the connection

**Use the service account credentials you created in Step 1!**

### Step 4: Test Connection

**Easiest way (PowerShell - no Python needed):**
```powershell
.\test-servicenow-connection-api.ps1
```

**Or via API directly:**
```powershell
# Replace {connection_id} with the ID from Step 2
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/settings/ticketing-connections/{connection_id}/test" -Method Post
```

**Or using Python (requires backend environment):**
```powershell
cd backend
python ..\test-servicenow-connection.py
```

### Step 5: Verify It's Working

Check the connection status again:
```powershell
.\check-servicenow-connection-simple.ps1
```

You should see:
- ✅ Connection active
- ✅ Last sync status: success
- ✅ Recent sync timestamp

## 🔍 Troubleshooting

### "No connections found"
- Connection wasn't created successfully
- Try Step 3 again
- Check backend logs for errors

### "401 Unauthorized"
- Wrong username/password
- Service account not active
- Service account missing required roles

### "403 Forbidden"
- Service account missing `sn_incident_read` or `sn_incident_write` roles
- Check ACLs (Access Control Lists) in ServiceNow

### "Connection timeout"
- ServiceNow instance URL incorrect
- Network/firewall blocking access
- ServiceNow instance not accessible

## 📚 Additional Resources

- **Service Account Setup**: `SERVICENOW_SERVICE_ACCOUNT_SETUP.md`
- **Full Integration Guide**: `SERVICENOW_INTEGRATION_SETUP.md`
- **Testing Guide**: `TEST_SERVICENOW_CONNECTION.md`

## ✅ Success Checklist

- [ ] Service account created in ServiceNow
- [ ] Required roles assigned to service account
- [ ] Connection created (check with `check-servicenow-connection-simple.ps1`)
- [ ] Connection test successful
- [ ] Can see incidents being fetched

## 🚀 Next Steps

Once connection is working:
1. Test webhook reception (optional)
2. Test status updates (resolve a ticket, check ServiceNow)
3. Set up monitoring tool integrations
4. Configure automatic runbook execution

