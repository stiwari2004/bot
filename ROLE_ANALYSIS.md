# Role System Analysis

## Current Database State

### Roles Found in Database:
- `admin` (legacy role - should be converted)
- `user` (standard user)
- `tenant_admin` (customer tenant admin)
- `super_admin` (platform admin - separate table)

### Missing Roles:
- `msp_admin` (MSP tenant admin)
- `viewer` (read-only user)

## Current User Data:

| ID | Email | Role | Tenant ID | Tenant Name | is_msp |
|----|-------|------|-----------|-------------|--------|
| 1 | demo@example.com | user | 1 | demo | False |
| 2 | admin@example.com | super_admin | 1 | demo | False |
| 3 | admin@platform.com | user | 1 | demo | False |
| 4 | admin@client.com | admin | 2 | Demo client | False |
| 5 | admin@client1.com | admin | 3 | client1 | **True** |
| 6 | admin@client2.com | admin | 4 | client2 | False |
| 7 | admin@client3.com | admin | 5 | client3 | **True** |
| 8 | demo@client3.com | user | 5 | client3 | **True** |
| 9 | admin@client31.com | admin | 5 | client3 | **True** |
| 10 | admin@client32.com | admin | 5 | client3 | **True** |
| 11 | admin@client33.com | tenant_admin | 6 | Client 31 | False |
| 12 | admin@client34.com | tenant_admin | 6 | Client 31 | False |

## Issues Found:

1. **Users with `role="admin"` in MSP tenants** (IDs 5, 7, 9, 10):
   - Should have `role="msp_admin"` 
   - Currently have `role="admin"` (legacy)

2. **Users with `role="admin"` in non-MSP tenants** (IDs 4, 6):
   - Should have `role="tenant_admin"`
   - Currently have `role="admin"` (legacy)

3. **Frontend MSP Admin User Creation Form**:
   - Shows: "user", "admin"
   - Should show: "user", "viewer", "tenant_admin" (or "Tenant Admin" label)

4. **User Model Comment**:
   - Says: `# admin, user, viewer`
   - Should say: `# user, viewer, tenant_admin, msp_admin, super_admin`

## Required Actions:

1. Update User model comment to reflect all roles
2. Fix frontend MSP admin form to show correct roles
3. Consider migration script to convert legacy `admin` roles to proper roles based on tenant type

