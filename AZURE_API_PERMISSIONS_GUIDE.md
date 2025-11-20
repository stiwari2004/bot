# Azure API Permissions & Setup Guide

## Problem: Discovery Still Not Working After Fixing Client Secret

Even after correcting the Client Secret value, discovery may still fail due to missing **API Permissions** in Azure AD.

## Root Cause Analysis

The Azure SDK uses **Azure Resource Manager (ARM) APIs** which require:
1. ✅ **Service Principal Authentication** (Client Secret) - You fixed this
2. ✅ **RBAC Permissions** (Reader role) - You have Owner role
3. ❌ **API Permissions in Azure AD** - This might be missing!

## Critical: API Permissions vs RBAC Permissions

These are **TWO DIFFERENT THINGS**:

### RBAC Permissions (Subscription Level)
- **What**: Permissions on Azure resources (VMs, resource groups, etc.)
- **Where**: Subscriptions → Access control (IAM) → Role assignments
- **Status**: ✅ You have Owner role (includes Reader)
- **Purpose**: Allows the service principal to **access** resources

### API Permissions (Azure AD App Registration)
- **What**: Permissions to **call Azure APIs** (Microsoft Graph, Azure Resource Manager)
- **Where**: Azure AD → App registrations → Your app → API permissions
- **Status**: ❓ **NEEDS TO BE CHECKED**
- **Purpose**: Allows the service principal to **authenticate and call APIs**

## Step-by-Step: Check and Configure API Permissions

### Step 1: Navigate to API Permissions

1. Go to **Azure Portal**: https://portal.azure.com
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find your app (Client ID: `b265b094-f556-4777-a066-656f069cdd0f`)
4. Click on the app
5. Click **API permissions** in the left menu

### Step 2: Check Current Permissions

Look at the list of permissions. You should see:

**Required Permissions:**
- ✅ **Azure Service Management** (user_impersonation) - **This is critical!**
- OR
- ✅ **Microsoft Graph** → **Directory.Read.All** (if using Graph API)

**If you see:**
- ❌ "No API permissions configured"
- ❌ Only "Microsoft Graph" permissions
- ❌ Only "User.Read" permission

**Then you need to add Azure Resource Manager permissions!**

### Step 3: Add Azure Service Management Permission

1. In **API permissions** page, click **+ Add a permission**
2. Select **Azure Service Management** (NOT Microsoft Graph)
3. Select **Delegated permissions**
4. Check **user_impersonation**
5. Click **Add permissions**

**OR** (if Azure Service Management is not available):

1. Click **+ Add a permission**
2. Select **APIs my organization uses**
3. Search for: **Azure Service Management**
4. Select it
5. Check **user_impersonation**
6. Click **Add permissions**

### Step 4: Grant Admin Consent

**CRITICAL STEP**: After adding permissions, you MUST grant admin consent:

1. Click **Grant admin consent for [Your Organization]**
2. Click **Yes** to confirm
3. Wait for the status to show **✓ Granted for [Your Organization]**

**Without admin consent, the permissions won't work!**

### Step 5: Verify Permissions

After granting consent, you should see:
- **Status**: ✅ **Granted for [Your Organization]** (green checkmark)
- **Type**: Delegated
- **API**: Azure Service Management
- **Permission**: user_impersonation

---

## Alternative: Use Application Permissions (More Secure)

If delegated permissions don't work, try **Application permissions**:

1. In **API permissions**, click **+ Add a permission**
2. Select **Azure Service Management**
3. Select **Application permissions** (not Delegated)
4. Check **user_impersonation**
5. Click **Add permissions**
6. **Grant admin consent**

---

## What If Azure Service Management Is Not Available?

Some tenants don't have "Azure Service Management" in the list. In that case:

### Option 1: Use Microsoft Graph (Limited)
1. Add **Microsoft Graph** → **Application permissions** → **Directory.Read.All**
2. Grant admin consent
3. **Note**: This may not be sufficient for Compute APIs

### Option 2: Register Azure Resource Manager API
1. In **API permissions**, click **+ Add a permission**
2. Select **APIs my organization uses**
3. Search for: **Windows Azure Service Management API**
4. Add **user_impersonation** permission
5. Grant admin consent

### Option 3: Use Default Permissions (May Work)
- The Azure SDK might work with just RBAC permissions
- But API permissions ensure proper authentication flow

---

## Additional Azure Configuration Checks

### Check 1: Resource Provider Registration

Some subscriptions require resource providers to be registered:

1. Go to **Subscriptions** → Your subscription
2. Click **Resource providers** in the left menu
3. Search for: **Microsoft.Compute**
4. Check if status is **Registered**
5. If not, click **Register** and wait 1-2 minutes

**Required Resource Providers:**
- ✅ **Microsoft.Compute** (for VMs)
- ✅ **Microsoft.Resources** (for resource groups)
- ✅ **Microsoft.Network** (for networking)

### Check 2: Subscription Status

1. Go to **Subscriptions** → Your subscription
2. Check **Status** - should be **Active**
3. If **Disabled** or **Warned**, you need to fix billing/account issues

### Check 3: Service Principal Status

1. Go to **Azure AD** → **App registrations** → Your app
2. Check **Status** - should be **Enabled**
3. Check **Certificates & secrets** - ensure secret is not expired

---

## Testing After Configuration

### Test 1: Verify API Permissions
```powershell
# Login with service principal
az login --service-principal -u YOUR_CLIENT_ID -p YOUR_CLIENT_SECRET --tenant YOUR_TENANT_ID

# Try to list VMs
az vm list --subscription YOUR_SUBSCRIPTION_ID --output table
```

If this works, the API permissions are correct.

### Test 2: Test in Application
1. Go to your application
2. Click **Test** on the Azure connection
3. Should show: "Azure connection successful! Found X resource groups and Y VMs."
4. Click **Discover**
5. Should list your VM(s)

---

## Common Issues and Solutions

### Issue 1: "Insufficient privileges to complete the operation"
**Solution**: Grant admin consent for API permissions

### Issue 2: "The client does not have authorization to perform action"
**Solution**: 
- Check RBAC permissions (Reader role at subscription level)
- Check API permissions (Azure Service Management)
- Grant admin consent

### Issue 3: "Resource provider not registered"
**Solution**: Register Microsoft.Compute resource provider

### Issue 4: "Authentication failed" (even with correct secret)
**Solution**: 
- Verify API permissions are granted
- Check if admin consent was granted
- Wait 2-3 minutes for propagation

---

## Summary Checklist

Before testing discovery, ensure:

- [ ] ✅ Client Secret **Value** (not ID) is correct
- [ ] ✅ RBAC Permission: **Reader** (or Owner/Contributor) at subscription level
- [ ] ✅ API Permission: **Azure Service Management** → **user_impersonation**
- [ ] ✅ **Admin consent** granted for API permissions
- [ ] ✅ Resource Provider: **Microsoft.Compute** is **Registered**
- [ ] ✅ Subscription status is **Active**
- [ ] ✅ Service principal secret is **not expired**

---

## Quick Reference

**Your Details:**
- **Tenant ID**: `60481b61-29cc-4fe7-bfe9-24bcafff9b67`
- **Client ID**: `b265b094-f556-4777-a066-656f069cdd0f`
- **Subscription ID**: `b80e9168-f3ac-4c55-9260-356cdf0233e0`

**Where to Check:**
1. **API Permissions**: Azure AD → App registrations → Your app → API permissions
2. **RBAC Permissions**: Subscriptions → Your subscription → Access control (IAM)
3. **Resource Providers**: Subscriptions → Your subscription → Resource providers

---

## Next Steps

1. **Check API Permissions** in Azure AD App Registration
2. **Add Azure Service Management** permission if missing
3. **Grant admin consent**
4. **Register Microsoft.Compute** resource provider if needed
5. **Test discovery** again

If still not working after these steps, check the backend logs for specific error messages.


