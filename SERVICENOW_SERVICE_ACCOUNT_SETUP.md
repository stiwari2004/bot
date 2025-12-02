# ServiceNow Service Account Setup Guide

## Why Use a Service Account?

✅ **Security Best Practice**: Don't use admin credentials for integrations
- Service accounts have limited, specific permissions
- Easier to audit and manage
- Can be disabled without affecting admin access
- Follows principle of least privilege

## Step-by-Step: Create ServiceNow Service Account

### Step 1: Create a New User

1. **Navigate to User Administration**:
   - Go to: `System Security > Users > Users`
   - Or search for "users" in the filter navigator

2. **Create New User**:
   - Click "New" button
   - Fill in the form:
     - **User ID**: `bot-integration` (or your preferred name)
     - **First Name**: `Bot`
     - **Last Name**: `Integration`
     - **Email**: `bot-integration@yourcompany.com` (optional but recommended)
     - **Active**: ✅ Checked
     - **Password**: Set a strong password (save it securely!)
     - **Password Needs Reset**: ❌ Unchecked (service accounts shouldn't require password reset)

3. **Click "Submit"**

### Step 2: Assign Required Roles

ServiceNow uses roles to control permissions. For basic incident operations, you need:

1. **Navigate to User Record**:
   - Open the user you just created
   - Go to the "Roles" tab

2. **Add Required Roles**:
   Click "Edit" and add these roles:
   
   **Required for REST API Access:**
   - `snc_platform_rest_api_access` - **REQUIRED** - Grants access to REST API (replaces deprecated `rest_service` role)
   - `itil` - ITIL role (allows incident access)
   
   **For Incident Table Access:**
   - `sn_incident_read` - Read incidents (recommended)
   - `sn_incident_write` - Write/update incidents (if you need to update tickets)
   
   **Optional but Recommended:**
   - `rest_api_explorer` - For API testing/exploration
   - `personalize_choices` - If you need to fetch field values/choices
   - `personalize_dictionary` - If you need field metadata
   
   **Note:** The `rest_service` role is **DEPRECATED**. Use `snc_platform_rest_api_access` instead.

3. **Click "Save"**

### Step 3: Verify Permissions

1. **Test API Access**:
   - Use the test script: `python test-servicenow-connection.py`
   - Or test via REST API directly

2. **Check Incident Access**:
   - Log in as the service account user
   - Verify you can:
     - View incidents
     - Create incidents
     - Update incidents
     - Add work notes

### Step 4: Use Service Account Credentials

**For Basic Auth:**
- **Username**: The User ID you created (e.g., `bot-integration`)
- **Password**: The password you set

**For OAuth 2.0:**
- Create an OAuth application (see next section)
- Use the service account for the OAuth application

## Alternative: OAuth 2.0 Setup (More Secure)

OAuth 2.0 is more secure than Basic Auth. Here's how to set it up:

### Step 1: Create OAuth Application

1. **Navigate to OAuth Applications**:
   - Go to: `System OAuth > Application Registry`
   - Or search for "application registry"

2. **Create New Application**:
   - Click "New"
   - Fill in:
     - **Name**: `Bot Integration`
     - **Redirect URL**: `https://your-bot-domain.com/api/v1/auth/callback` (or your callback URL)
     - **Active**: ✅ Checked
     - **Grant Types**: Select `client_credentials`
   - Click "Submit"

3. **Save Credentials**:
   - **Client ID**: Copy and save securely
   - **Client Secret**: Copy and save securely (shown only once!)

### Step 2: Assign Application to Service Account

1. **Navigate to Application**:
   - Open the OAuth application you created
   - Go to "Users" tab

2. **Add Service Account User**:
   - Click "Edit"
   - Add your service account user
   - Click "Save"

### Step 3: Use OAuth Credentials

- **Client ID**: From OAuth application
- **Client Secret**: From OAuth application

## Recommended Service Account Configuration

### User Settings:
- ✅ Active: Yes
- ✅ Password Never Expires: Yes (or set very long expiration)
- ❌ Password Needs Reset: No
- ❌ Multi-Factor Authentication: No (for service accounts)

### Roles (Minimum):
- `itil`
- `sn_incident_read`
- `sn_incident_write`
- `rest_api_explorer`

### Security:
- Use strong password (20+ characters, random)
- Store credentials securely (password manager, vault)
- Rotate credentials periodically (every 90 days recommended)
- Monitor service account activity

## Testing the Service Account

### Test 1: Basic Auth
```powershell
.\create-servicenow-connection.ps1 `
    -InstanceUrl "https://your-instance.service-now.com" `
    -Username "bot-integration" `
    -Password "your-service-account-password"
```

### Test 2: OAuth 2.0
```powershell
.\create-servicenow-connection.ps1 `
    -InstanceUrl "https://your-instance.service-now.com" `
    -ClientId "your-client-id" `
    -ClientSecret "your-client-secret"
```

### Test 3: Verify Connection
```bash
python check-servicenow-connection.py
python test-servicenow-connection.py
```

## Troubleshooting

### Issue: "Access Denied" or 403 Forbidden

**Solution**: 
- Verify service account has required roles
- Check incident table ACLs (Access Control Lists)
- Ensure service account is active

### Issue: "Invalid Credentials" or 401 Unauthorized

**Solution**:
- Verify username/password are correct
- Check if account is locked
- Verify account is active

### Issue: "Cannot Read Incidents"

**Solution**:
- Add `sn_incident_read` role
- Check ACLs for incident table
- Verify service account has ITIL role

## Security Checklist

- [ ] Service account created (not using admin)
- [ ] Strong password set (20+ characters)
- [ ] Password stored securely
- [ ] Minimum required roles assigned
- [ ] Account is active
- [ ] Password expiration set appropriately
- [ ] MFA disabled (for service accounts)
- [ ] Credentials documented securely
- [ ] Connection tested successfully

## Next Steps

1. ✅ Create service account
2. ✅ Assign required roles
3. ✅ Create connection using service account credentials
4. ✅ Test connection
5. ✅ Monitor connection status
6. ✅ Set up credential rotation schedule

