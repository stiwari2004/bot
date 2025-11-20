# Plan to Fix Azure Resource Discovery - Tomorrow

## Problem Identified from Logs

### Root Cause
**Invalid Client Secret**: The Azure credential (ID: 3) has the **Client Secret ID** instead of the **Client Secret Value**.

### Error Details
```
AADSTS7000215: Invalid client secret provided. 
Ensure the secret being sent in the request is the client secret value, 
not the client secret ID, for a secret added to app 'b265b094-f556-4777-a066-656f069cdd0f'
```

### What's Happening
1. ✅ **Connection found**: Connection 2 (aiops) with subscription_id `b80e9168-f3ac-4c55-9260-356cdf0233e0`
2. ✅ **Credentials loaded**: Tenant ID, Client ID, and "secret" are present
3. ❌ **Authentication fails**: Azure rejects the secret because it's the **Secret ID** (GUID) not the **Secret Value** (long string)

### Log Evidence
- Line 695-698: `Processing connection 2: subscription_id=b80e9168-f3ac-4c55-9260-356cdf0233e0, has_tenant=True, has_client_id=True, has_secret=***`
- Line 730-737: `Invalid client secret provided. Ensure the secret being sent in the request is the client secret value, not the client secret ID`
- Line 814-817: `list_azure_vms returned 0 total VMs` (because authentication failed)

---

## Solution Steps for Tomorrow

### Step 1: Get the Correct Client Secret Value

1. Go to **Azure Portal**: https://portal.azure.com
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find your app: Search for Client ID `b265b094-f556-4777-a066-656f069cdd0f` (from the error)
   - OR find it by the Application name you created
4. Click on the app → **Certificates & secrets** (left menu)
5. Under **Client secrets**, you'll see:
   - **Secret ID** (GUID like: `12345678-1234-1234-1234-123456789abc`) ❌ **This is what you have**
   - **Value** (long string like: `abc~DEF123ghi456JKL789mno012PQR345stu678VWX901yz`) ✅ **This is what you need**
6. **Important**: 
   - If the secret value is hidden (shows as dots), you need to **create a new secret**
   - Azure only shows the secret value **once** when you create it
   - If you can't see it, you must create a new one

### Step 2: Create New Client Secret (If Value Not Visible)

1. In **Certificates & secrets** → Click **+ New client secret**
2. Enter a **Description** (e.g., "Bot Tool Secret")
3. Choose **Expires** (recommend: 24 months)
4. Click **Add**
5. **IMMEDIATELY COPY THE VALUE** - it will only show once!
   - The value looks like: `abc~DEF123ghi456JKL789mno012PQR345stu678VWX901yz`
   - This is different from the Secret ID (GUID)

### Step 3: Update the Credential in the Tool

1. Go to your application: **Settings** → **Infrastructure Connections**
2. Find your Azure credential (the one used by connection "aiops")
3. Click **Edit** on the credential
4. Update the **Client Secret** field with the **Secret Value** (not the ID)
5. Save

### Step 4: Test Again

1. Click **Test** on the Azure connection - should show success
2. Click **Discover** - should now list your VM(s)

---

## Additional Issues Found (Secondary)

### Issue 1: Old Credential (ID: 1) - Can Ignore
- Connection 1 uses credential ID 1, which was encrypted with old key
- This is skipped automatically, so not blocking discovery
- **Action**: Can delete this old credential if not needed

### Issue 2: Connection Type Mismatch
- Connection 2 has `connection_type=azure_bastion`
- But it's being used for cloud account discovery
- **Action**: Consider changing connection type to `cloud_account` or `azure_subscription` for clarity
- **Note**: This doesn't block functionality, just a naming issue

---

## Quick Reference

### What You Need
- **Tenant ID**: `60481b61-29cc-4fe7-bfe9-24bcafff9b67` (from logs)
- **Client ID**: `b265b094-f556-4777-a066-656f069cdd0f` (from error message)
- **Client Secret**: The **VALUE** (long string), not the ID (GUID)
- **Subscription ID**: `b80e9168-f3ac-4c55-9260-356cdf0233e0` ✅ (correct)

### Where to Find Client Secret Value
1. Azure Portal → Azure AD → App registrations
2. Your app → Certificates & secrets
3. Client secrets section → Copy the **Value** column
4. If hidden, create new secret and copy immediately

---

## Expected Outcome After Fix

After updating the Client Secret with the correct **Value**:

1. **Test** should show: `"Azure connection successful! Found X resource groups and Y VMs."`
2. **Discover** should return: `{connection_id: 2, resources: [{name: "your-vm-name", ...}], total: 1}`
3. Your stopped/deallocated VM should appear in the list

---

## Summary

**The fix is simple**: Update the Azure credential's Client Secret field with the **Secret Value** (long string) instead of the **Secret ID** (GUID).

The rest of the setup is correct:
- ✅ Subscription ID matches
- ✅ Permissions (Owner role) are set
- ✅ Connection is configured
- ✅ VM exists in Azure
- ❌ Only the Client Secret value is wrong

Once this is fixed, discovery should work immediately.

---

## Additional Checks After Fixing Client Secret

If discovery still doesn't work after fixing the Client Secret, check:

### 1. API Permissions in Azure AD
- Go to: **Azure AD** → **App registrations** → Your app → **API permissions**
- Ensure **Azure Service Management** → **user_impersonation** is added
- **Grant admin consent** (critical step!)

### 2. Resource Provider Registration
- Go to: **Subscriptions** → Your subscription → **Resource providers**
- Ensure **Microsoft.Compute** is **Registered**
- If not, click **Register** and wait 1-2 minutes

### 3. Check Backend Logs
After clicking "Discover", check logs:
```powershell
docker-compose logs backend --tail=100 | Select-String -Pattern "Azure API|VM|error|Error" -Context 2
```

Look for:
- `"Azure API returned X VMs"` - This tells you if Azure is returning VMs
- Any authentication or permission errors
- Specific error messages about what's failing

See `AZURE_API_PERMISSIONS_GUIDE.md` for detailed troubleshooting.


