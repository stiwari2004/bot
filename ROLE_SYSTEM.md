# Role System Definition

## Roles Overview

### 1. **super_admin**
- **Access**: `/super-admin`
- **Scope**: Platform-wide
- **Model**: Separate `SuperAdmin` table (not in `users` table)
- **Can Do**:
  - Manage all tenants (MSPs and regular tenants)
  - Create/update/delete tenants
  - Manage all users across all tenants
  - Create subscriptions
  - View all billing
  - System-wide configuration

### 2. **msp_admin**
- **Access**: `/tenant-admin`
- **Scope**: MSP tenant and its customers (sub-tenants)
- **Model**: `users` table with `role="msp_admin"` AND `tenant.is_msp=True`
- **Can Do**:
  - Create/update/delete customer tenants (sub-tenants)
  - Manage users for customer tenants ONLY (not MSP's own tenant)
  - Create subscriptions for customers
  - View billing for customers
  - Manage customer nodes
- **Cannot Do**:
  - Create users in MSP's own tenant
  - Access other MSPs' data
  - Access super admin features

### 3. **tenant_admin**
- **Access**: `/admin`
- **Scope**: Their own tenant only (non-MSP tenant)
- **Model**: `users` table with `role="tenant_admin"` AND `tenant.is_msp=False`
- **Can Do**:
  - Manage users in their tenant (can only create user/viewer roles)
  - View billing for their tenant (read-only)
  - Approve/disapprove nodes
  - Access settings & connections
  - View system health for their tenant
- **Cannot Do**:
  - Create other tenant admins
  - Access other tenants' data
  - Create subscriptions (read-only)
  - Access MSP admin features

### 4. **user**
- **Access**: `/` (main user page)
- **Scope**: Their own tenant
- **Model**: `users` table with `role="user"`
- **Can Do**:
  - View tickets
  - Execute runbooks
  - View executions
  - View runbooks
  - View analytics

### 5. **viewer**
- **Access**: `/` (main user page, read-only)
- **Scope**: Their own tenant
- **Model**: `users` table with `role="viewer"`
- **Can Do**: Read-only access to tickets, runbooks, executions, analytics

## Role Assignment Rules

### When Creating Users:

1. **Super Admin creates tenant with admin user**:
   - If tenant `is_msp=True`: Admin user gets `role="msp_admin"`
   - If tenant `is_msp=False`: Admin user gets `role="tenant_admin"`

2. **Super Admin creates user for tenant**:
   - If `role="admin"` and tenant `is_msp=True`: → `role="msp_admin"`
   - If `role="admin"` and tenant `is_msp=False`: → `role="tenant_admin"`
   - Other roles: Keep as-is

3. **MSP Admin creates customer**:
   - Customer tenant admin gets `role="tenant_admin"` (always)

4. **MSP Admin creates user for customer**:
   - If `role="admin"`: → `role="tenant_admin"`
   - Other roles: Keep as-is

5. **Tenant Admin creates user**:
   - Can only create `role="user"` or `role="viewer"`
   - Cannot create admin roles

## Access Control Matrix

| Role | /super-admin | /tenant-admin | /admin | / |
|------|--------------|---------------|--------|---|
| super_admin | ✅ | ❌ | ❌ | ❌ |
| msp_admin | ❌ | ✅ | ❌ | ❌ |
| tenant_admin | ❌ | ❌ | ✅ | ❌ |
| user | ❌ | ❌ | ❌ | ✅ |
| viewer | ❌ | ❌ | ❌ | ✅ (read-only) |

## Backward Compatibility

- Legacy `role="admin"` with `tenant.is_msp=True` → treated as `msp_admin`
- Legacy `role="admin"` with `tenant.is_msp=False` → treated as `tenant_admin`

