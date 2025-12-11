# Super Admin Implementation

## Overview

The system now has two types of admin:

1. **Tenant Admin** (`role: "admin"`) - Manages users within their own tenant
   - Access: `/admin` (existing admin dashboard)
   - Can only see/manage users in their tenant
   - Can only view their own tenant information

2. **Super Admin** (`role: "super_admin"`) - Platform-level administrator
   - Access: `/super-admin` (new separate page)
   - Can manage all tenants
   - Can manage all users across all tenants
   - Can create tenants and assign users to any tenant

## Backend Changes

### New Files
- `backend/app/api/v1/endpoints/super_admin.py` - Super admin endpoints
- `backend/app/services/auth.py` - Added `get_current_super_admin_user()` function

### Updated Files
- `backend/app/api/v1/api.py` - Added super admin router
- `backend/app/api/v1/endpoints/admin.py` - Made tenant-scoped (only shows current user's tenant)

### API Endpoints

**Super Admin Endpoints** (`/api/v1/super-admin/*`):
- `GET /tenants` - List all tenants
- `POST /tenants` - Create tenant
- `GET /tenants/{id}` - Get tenant details
- `PATCH /tenants/{id}` - Update tenant
- `GET /users` - List all users (optionally filtered by tenant)
- `POST /users` - Create user in any tenant
- `GET /users/{id}` - Get user details
- `PATCH /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user
- `GET /overview` - Platform-wide statistics

**Tenant Admin Endpoints** (`/api/v1/admin/*`):
- `GET /tenants` - Get current user's tenant only
- `GET /users` - List users in current user's tenant only
- `POST /users` - Create user in current user's tenant only
- `GET /overview` - Tenant-scoped statistics

## Frontend Changes

### New Files
- `frontend-nextjs/src/features/super-admin/` - Super admin feature folder
  - `types.ts` - TypeScript types
  - `hooks/useSuperAdmin.ts` - React hook for super admin API calls
  - `components/SuperAdminDashboard.tsx` - Main dashboard
  - `components/SystemOverview.tsx` - Platform overview
  - `components/TenantManagement.tsx` - Tenant management
  - `components/UserManagement.tsx` - User management
  - `components/CreateTenantModal.tsx` - Create tenant modal
  - `components/EditTenantModal.tsx` - Edit tenant modal
  - `components/CreateUserModal.tsx` - Create user modal
  - `components/EditUserModal.tsx` - Edit user modal

### Updated Files
- `frontend-nextjs/src/lib/api-config.ts` - Added super admin endpoints
- `frontend-nextjs/src/app/page.tsx` - Added super admin navigation item

## Creating a Super Admin User

To create a super admin user, use the script:

```bash
docker-compose exec backend python scripts/create_admin_user.py superadmin@example.com password123 1 --role super_admin
```

Or update the script to support super_admin role:

```python
# In backend/scripts/create_admin_user.py
# Add --role parameter support
```

## Navigation

- **Tenant Admin** (`role: "admin"`): Sees "Administration" link → `/admin` (tenant-scoped)
- **Super Admin** (`role: "super_admin"`): Sees "Super Admin" link → `/super-admin` (platform-level)

## Security

- Super admin endpoints require `role: "super_admin"`
- Tenant admin endpoints require `role: "admin"` or `"super_admin"` (but are tenant-scoped)
- Super admin can access tenant admin endpoints but sees platform-wide data
- Tenant admin cannot access super admin endpoints

## Next Steps

1. Update `create_admin_user.py` script to support `--role super_admin`
2. Create super admin components (can copy from admin components and adapt)
3. Update navigation in `page.tsx` to show super admin link for super_admin users
4. Test both admin types







