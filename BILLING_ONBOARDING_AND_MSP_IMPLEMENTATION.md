# Billing Onboarding & MSP White-Labeling Implementation

## ✅ What's Been Implemented

### 1. Billing Configuration During Tenant Onboarding

**Backend Changes:**
- Updated `TenantCreate` schema to include optional `billing_config`
- Modified `create_tenant` endpoint to create billing configuration during tenant creation
- Billing config is created automatically if provided during onboarding

**Frontend Changes:**
- Added billing configuration section to tenant creation modal
- Toggle to enable/disable billing configuration during creation
- Form fields for:
  - Fixed monthly cost
  - Per-node billing (enable/disable, cost)
  - Per-ticket-received billing
  - Per-ticket-resolved billing
  - Per-execution billing

**Usage:**
1. Go to Super Admin → Tenants → Create Tenant
2. Fill in tenant details
3. Check "Configure Billing Now" to enable billing configuration
4. Set up billing model (fixed + variable costs)
5. Create tenant with billing configured

---

### 2. MSP/White-Labeling Support

**Backend Changes:**
- Added `is_msp` field to `Tenant` model (marks tenant as MSP/reseller)
- Added `parent_tenant_id` field to `Tenant` model (links sub-tenants to parent MSP)
- Created `tenant_admin.py` endpoints for MSPs to manage their customers:
  - `GET /api/v1/tenant-admin/customers` - List all customers
  - `POST /api/v1/tenant-admin/customers` - Create new customer
  - `GET /api/v1/tenant-admin/customers/{id}` - Get customer details

**Features:**
- MSP tenants can create sub-tenants (customers)
- Each customer gets their own admin user
- Billing configuration can be set during customer creation
- Parent-child relationship maintained for billing/reporting

**Database Migration:**
```sql
-- Run: backend/sql/add_msp_fields.sql
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS is_msp BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS parent_tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL;
```

---

### 3. Tenant Admin System

**For MSPs (White-label Resellers):**
- MSP tenants marked with `is_msp = true`
- MSP admin users (role="admin" in MSP tenant) can:
  - Create customer tenants
  - Set billing configuration for each customer
  - View all their customers
  - Manage customer details

**Access Control:**
- Only users with `role="admin"` in an MSP tenant can access tenant-admin endpoints
- Endpoints automatically filter to show only customers of the current MSP

---

## 📋 Next Steps

### 1. Run Database Migration
```bash
docker-compose exec postgres psql -U postgres -d troubleshooting_ai -f /app/sql/add_msp_fields.sql
```

Or manually:
```sql
-- Copy from backend/sql/add_msp_fields.sql
```

### 2. Create Frontend Tenant Admin Page
Create `/app/tenant-admin/customers/page.tsx` for MSPs to:
- List their customers
- Create new customers
- View/edit customer details
- Configure billing for customers

### 3. Add Navigation
- Add "Customer Management" link in main navigation for MSP admin users
- Show only if user's tenant has `is_msp = true`

---

## 🎯 Usage Examples

### Creating an MSP Tenant (Super Admin)
```json
POST /api/v1/super-admin/tenants
{
  "name": "TechSolutions MSP",
  "is_msp": true,
  "billing_config": {
    "fixed_monthly_cost": 9999,
    "per_node_enabled": true,
    "per_node_cost": 999
  }
}
```

### MSP Creating a Customer (Tenant Admin)
```json
POST /api/v1/tenant-admin/customers
{
  "name": "Acme Corporation",
  "admin_email": "admin@acme.com",
  "admin_password": "secure123",
  "billing_config": {
    "fixed_monthly_cost": 4999,
    "per_ticket_received_enabled": true,
    "per_ticket_received_cost": 10
  }
}
```

---

## 📝 API Endpoints

### Super Admin (Platform Level)
- `POST /api/v1/super-admin/tenants` - Create tenant (with billing config)
- `GET /api/v1/billing/config/{tenant_id}` - Get billing config
- `PUT /api/v1/billing/config/{tenant_id}` - Update billing config

### Tenant Admin (MSP Level)
- `GET /api/v1/tenant-admin/customers` - List customers
- `POST /api/v1/tenant-admin/customers` - Create customer
- `GET /api/v1/tenant-admin/customers/{id}` - Get customer details

---

## 🔐 Access Control

1. **Super Admin**: Full platform access, can create MSPs and regular tenants
2. **MSP Admin**: Can create/manage their own customers (sub-tenants)
3. **Customer Admin**: Regular tenant admin, manages their own tenant only

---

## ✨ Key Features

✅ **Billing Configuration During Onboarding**: Set up billing when creating tenant
✅ **MSP Support**: Mark tenants as MSPs that can create sub-tenants
✅ **White-Labeling**: MSPs can manage their own customers independently
✅ **Hierarchical Structure**: Parent-child relationship for billing/reporting
✅ **Flexible Billing**: Configure fixed + variable costs per tenant

---

## 🚀 Ready to Use

The backend is complete and ready. Next:
1. Run database migration for MSP fields
2. Create frontend tenant admin page
3. Test the full flow: Super Admin → Create MSP → MSP creates customers


