# Customer Tenant Setup Guide

This guide shows how to create a customer tenant with a custom URL path like `/c/customer-name`.

## Quick Setup

### 1. Create Customer Tenant

Run the script on your server:

```bash
cd /home/opsbot/bot
docker compose -f docker-compose.production.yml exec backend python scripts/create_customer_tenant.py \
  --name "Acme Corporation" \
  --slug "acme-corp" \
  --email "admin@acme.com" \
  --password "SecurePassword123!" \
  --full-name "Acme Admin" \
  --description "Acme Corporation customer tenant"
```

**Parameters:**
- `--name`: Display name for the tenant (e.g., "Acme Corporation")
- `--slug`: URL-friendly slug (e.g., "acme-corp") - used in `/c/acme-corp`
- `--email`: Admin user email for this tenant
- `--password`: Admin user password
- `--full-name`: (Optional) Full name for the admin user
- `--description`: (Optional) Tenant description

### 2. Access the Customer Portal

Once created, the customer can access their portal at:

```
https://demo.resolvify.tech/c/acme-corp
```

This will:
- Show login page if not authenticated
- Redirect to main app after login
- The user's tenant context is automatically set based on their account

### 3. Share Credentials

Share the login credentials with your customer:
- **URL**: `https://demo.resolvify.tech/c/acme-corp`
- **Email**: `admin@acme.com`
- **Password**: `SecurePassword123!`

## How It Works

1. **Tenant Creation**: The script creates a tenant with a `subdomain_slug` field
2. **User Creation**: Creates a `tenant_admin` user for that tenant
3. **Custom Route**: The `/c/[slug]` route in Next.js handles the custom path
4. **Tenant Isolation**: All data is automatically isolated by `tenant_id`

## Example: Creating Multiple Customers

```bash
# Customer 1
docker compose -f docker-compose.production.yml exec backend python scripts/create_customer_tenant.py \
  --name "TechCorp" \
  --slug "techcorp" \
  --email "admin@techcorp.com" \
  --password "TechCorp2024!"

# Customer 2
docker compose -f docker-compose.production.yml exec backend python scripts/create_customer_tenant.py \
  --name "StartupXYZ" \
  --slug "startupxyz" \
  --email "admin@startupxyz.com" \
  --password "StartupXYZ2024!"
```

## Cleanup (After Demo Period)

To remove a customer tenant:

```bash
# Connect to database
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai

# Delete tenant (this will cascade delete users and related data)
DELETE FROM tenants WHERE subdomain_slug = 'acme-corp';
```

**Note**: This will permanently delete all data for that tenant. Make sure to export any needed data first.

## Troubleshooting

### Slug Already Exists
If you get an error that the slug already exists, choose a different slug:
```bash
--slug "acme-corp-v2"
```

### User Email Already Exists
If the email is already in use, use a different email or delete the existing user first.

### Access Issues
- Make sure the tenant is `is_active = true`
- Verify the user's `is_active = true`
- Check that the user's `tenant_id` matches the tenant

