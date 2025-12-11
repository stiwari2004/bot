# Tenant URL Guide

## Overview

When you create a tenant (e.g., "Ritwik"), the system automatically generates a URL-friendly slug from the tenant name. This guide explains how to access tenant-specific URLs.

## URL Structure

### For Tenant "Ritwik"

When you create a tenant named "Ritwik", the system:
1. Generates a slug: `ritwik` (lowercase, URL-friendly)
2. Creates access URLs for that tenant

### Access URLs

#### Option 1: Direct Tenant Path (Recommended)
- **URL**: `https://resolvify.tech/ritwik`
- **What it does**: 
  - If not logged in → redirects to login page
  - If logged in → shows the main application for that tenant
  - The slug is stored in sessionStorage to maintain tenant context

#### Option 2: Customer Path (Alternative)
- **URL**: `https://resolvify.tech/c/ritwik`
- **What it does**: Same as above, but uses the `/c/` prefix

### Tenant Admin URLs

#### For MSP Admins (Multi-tenant administrators)
- **Login URL**: `https://resolvify.tech/tenant-admin/login`
- **Dashboard URL**: `https://resolvify.tech/tenant-admin`
- **Features**: Manage multiple customer tenants, subscriptions, users across tenants

#### For Regular Tenant Admins (Single tenant administrators)
- **Login URL**: `https://resolvify.tech/` (main login page)
- **Admin Features**: Available in the main app under "System" section
- **Features**: Manage users, nodes, billing for their specific tenant

### Super Admin URLs

- **Login URL**: `https://admin.resolvify.tech` (auto-redirects to `/super-admin/login`)
- **Dashboard URL**: `https://admin.resolvify.tech/super-admin`
- **Features**: Platform-wide management, create/manage all tenants

## How It Works

### Slug Generation

When creating a tenant named "Ritwik":
1. The backend uses `slugify()` function to convert "Ritwik" → "ritwik"
2. If "ritwik" already exists, it appends a number: "ritwik-1", "ritwik-2", etc.
3. The slug is stored in the `tenants.subdomain_slug` field

### Authentication Flow

1. **User visits** `https://resolvify.tech/ritwik`
2. **If not authenticated**:
   - Slug is stored in `sessionStorage` as `customer_slug`
   - User is redirected to login page: `/?customer_slug=ritwik`
3. **User logs in** with their email/password
4. **After login**:
   - Backend returns JWT token with `tenant_id`
   - Frontend redirects to main app
   - User sees data for their tenant (based on `tenant_id` in token)

### Reserved Paths

These paths are reserved and won't be treated as tenant slugs:
- `/admin` - Tenant admin features
- `/super-admin` - Super admin dashboard
- `/tenant-admin` - MSP admin dashboard
- `/api` - API endpoints
- `/c` - Customer path prefix
- `/health` - Health check endpoint

## Example: Ritwik Tenant

Assuming you created a tenant named "Ritwik":

### For End Users
- **Access URL**: `https://resolvify.tech/ritwik`
- **Login**: Use the tenant admin's email/password
- **What they see**: Main application with tickets, runbooks, executions, etc.

### For Tenant Admin
- **Access URL**: `https://resolvify.tech/ritwik` or `https://resolvify.tech/`
- **Login**: Use tenant admin credentials
- **Admin Features**: Available in "System" section (Users, Nodes, Billing)

### For MSP Admin (if Ritwik is a customer of an MSP)
- **Access URL**: `https://resolvify.tech/tenant-admin`
- **Login**: Use MSP admin credentials
- **Can manage**: Ritwik tenant along with other customer tenants

## Finding the Slug

To find the exact slug for a tenant, you can:

1. **Via Super Admin Dashboard**:
   - Go to `https://admin.resolvify.tech/super-admin/tenants`
   - Find "Ritwik" in the tenant list
   - Check the "Subdomain Slug" column

2. **Via API** (if you have super admin token):
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://resolvify.tech/api/v1/super-admin/tenants
   ```

3. **Via Database** (direct access):
   ```sql
   SELECT name, subdomain_slug FROM tenants WHERE name = 'Ritwik';
   ```

## Notes

- The slug is case-insensitive: `ritwik`, `Ritwik`, `RITWIK` all work
- The slug must be unique across all tenants
- If a tenant name changes, the slug doesn't automatically update (you'd need to manually update `subdomain_slug` in the database)
- The `/ritwik` route was added in the latest code update and will be available after deployment

