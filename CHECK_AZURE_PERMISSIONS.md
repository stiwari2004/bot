# How to Check and Fix Azure Service Principal Permissions

## Problem
Your service principal can authenticate but cannot list VMs. This means it needs the **"Reader"** role.

## Step-by-Step Guide

### Step 1: Find Your Service Principal (Client ID)

1. Go to your application settings in the tool
2. Find your Azure credential
3. Copy the **Client ID** (also called Application ID)

OR

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find your application (the one you created for this tool)
4. Copy the **Application (client) ID**

---

### Step 2: Check Current Permissions

#### Option A: Check at Subscription Level (Recommended)

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to: **Subscriptions** → **Azure subscription 1** (or your subscription name)
3. Click on **Access control (IAM)** in the left menu
4. Click on **Role assignments** tab
5. Look for your service principal (Client ID) in the list
6. Check if it has any of these roles:
   - ✅ **Reader** (minimum required)
   - ✅ **Contributor** (includes Reader)
   - ✅ **Owner** (includes Reader)

**If your service principal is NOT in the list**, you need to add it (see Step 3).

#### Option B: Check at Resource Group Level

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to: **Resource groups** → **infrabottest**
3. Click on **Access control (IAM)** in the left menu
4. Click on **Role assignments** tab
5. Look for your service principal (Client ID)

**Note**: Subscription-level permissions are recommended as they apply to all resources.

---

### Step 3: Assign "Reader" Role to Service Principal

#### At Subscription Level (Recommended):

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to: **Subscriptions** → **Azure subscription 1**
3. Click on **Access control (IAM)** in the left menu
4. Click **+ Add** → **Add role assignment**
5. In the **Role** tab:
   - Search for: **Reader**
   - Select **Reader** role
   - Click **Next**
6. In the **Members** tab:
   - Click **+ Select members**
   - Search for your service principal by:
     - **Application (client) ID** (the Client ID from your credential)
     - OR **Application name** (if you know it)
   - Select your service principal
   - Click **Select**
   - Click **Next**
7. In the **Review + assign** tab:
   - Review the assignment
   - Click **Review + assign**

**Wait 1-2 minutes** for the role assignment to propagate.

#### At Resource Group Level (Alternative):

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to: **Resource groups** → **infrabottest**
3. Click on **Access control (IAM)** in the left menu
4. Click **+ Add** → **Add role assignment**
5. Follow the same steps as above

---

### Step 4: Verify the Fix

1. Go back to your application
2. Click **Test** on your Azure connection
3. You should now see: **"Azure connection successful! Found X resource groups and Y VMs."**
4. Click **Discover** to see your VMs listed

---

### Step 5: Troubleshooting

If it still doesn't work after assigning Reader role:

1. **Wait 2-3 minutes** - Role assignments can take time to propagate
2. **Check the exact error** in backend logs:
   ```powershell
   docker-compose logs backend --tail=50 | Select-String -Pattern "Azure|permission|403"
   ```
3. **Verify Client ID matches** - Make sure the Client ID in your credential matches the Application ID in Azure Portal
4. **Check if service principal is enabled** - In Azure AD → App registrations → Your app → Overview, ensure it's not disabled

---

## Quick PowerShell Check (If Azure CLI is installed)

```powershell
# Login to Azure
az login

# Set subscription
az account set --subscription "b80e9168-f3ac-4c55-9260-356cdf0233e0"

# Check role assignments at subscription level
az role assignment list --scope /subscriptions/b80e9168-f3ac-4c55-9260-356cdf0233e0 --output table

# Check role assignments at resource group level
az role assignment list --scope /subscriptions/b80e9168-f3ac-4c55-9260-356cdf0233e0/resourceGroups/infrabottest --output table
```

Replace `YOUR_CLIENT_ID` with your actual Client ID to filter:
```powershell
az role assignment list --scope /subscriptions/b80e9168-f3ac-4c55-9260-356cdf0233e0 --assignee YOUR_CLIENT_ID --output table
```

---

## Common Issues

### Issue: "Cannot find service principal"
- **Solution**: Make sure you're searching by the **Application (client) ID**, not the display name
- The Client ID is a GUID like: `12345678-1234-1234-1234-123456789abc`

### Issue: "Role assignment already exists"
- **Solution**: The service principal already has permissions. Check if it's the correct role (Reader, Contributor, or Owner)

### Issue: "Still getting permission denied after assigning role"
- **Solution**: 
  1. Wait 2-3 minutes for propagation
  2. Restart the backend: `docker-compose restart backend`
  3. Try again

---

## Summary

**Minimum Required Permission**: **Reader** role at subscription level

**Your Subscription ID**: `b80e9168-f3ac-4c55-9260-356cdf0233e0`

**Your Resource Group**: `infrabottest`

**Your VM**: Exists and is stopped (deallocated) - should still be discoverable



