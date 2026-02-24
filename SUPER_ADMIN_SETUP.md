# Super Admin Setup Guide

## Overview

The Super Admin system provides platform-level administration for managing tenants, users, and system configuration. It uses a **separate authentication system** from regular tenant users for security.

## Architecture

### Backend

1. **SuperAdmin Model** (`backend/app/models/super_admin.py`)
   - Separate table for super admin users
   - No tenant_id (platform-level only)
   - Separate from regular User model

2. **Super Admin Auth Service** (`backend/app/services/super_admin_auth.py`)
   - Separate OAuth2 scheme
   - JWT tokens with `admin_type: "super_admin"` claim
   - 8-hour session duration (longer than regular users)

3. **API Endpoints**
   - `/api/v1/super-admin/auth/login` - Super admin login
   - `/api/v1/super-admin/auth/me` - Get current super admin
   - `/api/v1/super-admin/overview` - Platform statistics
   - `/api/v1/super-admin/tenants` - Tenant management (CRUD)
   - `/api/v1/super-admin/tenants/{id}/users` - Tenant user management

### Frontend

1. **Super Admin Auth Context** (`frontend-nextjs/src/contexts/SuperAdminAuthContext.tsx`)
   - Separate auth state management
   - Uses `super_admin_token` in localStorage

2. **Routes**
   - `/super-admin/login` - Super admin login page
   - `/super-admin` - Super admin dashboard

3. **Layout** (`frontend-nextjs/src/app/super-admin/layout.tsx`)
   - Wraps all super admin routes
   - Handles authentication redirects
   - Protects routes (except login)

## Setup Instructions

### 1. Create First Super Admin User

Run the script to create your first super admin:

```bash
cd backend
python scripts/create_super_admin.py admin@platform.com yourpassword "Platform Admin"
```

Or with Docker:

```bash
docker-compose exec backend python scripts/create_super_admin.py admin@platform.com yourpassword "Platform Admin"
```

### 2. Access Super Admin Portal

1. Navigate to: **`/super-admin/login`** (e.g. `https://your-domain/super-admin/login` or `http://localhost:3000/super-admin/login`)
2. Login with your **super admin** credentials (email/password from `super_admins` table)
3. You'll be redirected to the dashboard at `/super-admin`

**Important:** The **main** login page (`/` or `/login`) uses the **users** table (tenant users). Super admin uses the **super_admins** table and a **separate** login at **`/super-admin/login`**. If you see "Login attempt with non-existent email" in logs when using the main login, you are hitting the wrong endpoint — use `/super-admin/login` for super admin.

### 3. Reset Super Admin Password (e.g. production)

If the super admin account exists but the password doesn't work, reset it by running the script **inside the backend container** (so it uses the same DB and hashing as the app):

```bash
# Production (docker-compose.production.yml, project bot-prod)
docker exec -it bot-prod-backend python scripts/reset_super_admin_password.py admin@resolvify.tech 'YourNewPassword123!'
```

Use a **strong password** and single quotes around it so the shell doesn't expand it. Then log in at **`/super-admin/login`** with that email and new password.

### 4. Database Migration

The new `super_admins` table and updated `tenants` table will be created automatically on next backend startup. If you need to manually run migrations:

```bash
# The tables are created via SQLAlchemy on startup
# Just restart the backend service
docker-compose restart backend
```

## Features

### Current Implementation (Phase 1)

✅ **Super Admin Authentication**
- Separate login system
- JWT-based authentication
- Session management

✅ **Dashboard**
- Platform overview statistics
- Total tenants (SaaS vs PaaS)
- Total users across all tenants
- Quick action buttons

✅ **Tenant Management API**
- List all tenants
- Create tenant (with SaaS/PaaS type)
- Get tenant details
- Update tenant
- Deactivate tenant

✅ **Tenant User Management API**
- List users for a tenant
- Create user for a tenant

### Enhanced Tenant Model

The `Tenant` model now includes:

- `subdomain_slug` - For future subdomain routing
- `deployment_type` - 'saas' or 'paas'
- `platform_managed` - Boolean flag
- `setup_token` - For PaaS onboarding
- `onboarding_status` - pending, in_progress, completed, failed
- `contact_email`, `contact_name`, `contact_phone` - Contact info
- `config_metadata` - JSON field for tenant configuration

## API Usage Examples

### Login

```bash
curl -X POST http://localhost:8000/api/v1/super-admin/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@platform.com&password=yourpassword"
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "admin": {
    "id": 1,
    "email": "admin@platform.com",
    "full_name": "Platform Admin",
    "is_active": true
  }
}
```

### Get Platform Overview

```bash
curl -X GET http://localhost:8000/api/v1/super-admin/overview \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Tenant

```bash
curl -X POST http://localhost:8000/api/v1/super-admin/tenants \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "deployment_type": "saas",
    "contact_email": "admin@acme.com",
    "contact_name": "John Doe"
  }'
```

### List Tenants

```bash
curl -X GET "http://localhost:8000/api/v1/super-admin/tenants?deployment_type=saas&is_active=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Security Considerations

1. **Separate Authentication**: Super admins use a completely separate login system
2. **No Tenant Context**: Super admins don't have a tenant_id and can access all tenants
3. **RLS Bypass**: Super admins bypass Row-Level Security (they don't set tenant context)
4. **Token Claims**: Super admin tokens include `admin_type: "super_admin"` to distinguish from regular users

## Next Steps (Future Phases)

- [ ] Tenant detail page with tabs (Overview, Connections, Users, Settings)
- [ ] Connection management UI (ticketing, monitoring, infrastructure)
- [ ] Credential management UI
- [ ] Tenant onboarding flows (SaaS vs PaaS)
- [ ] Setup token generation for PaaS tenants
- [ ] Welcome email templates
- [ ] Activity/audit logging UI
- [ ] Subdomain routing (when going live)

## Troubleshooting

### "Cannot connect to backend" error

Make sure the backend is running:
```bash
docker-compose ps backend
docker-compose logs backend
```

### "401 Unauthorized" on login

1. Verify super admin user exists:
   ```bash
   docker-compose exec backend python scripts/create_super_admin.py admin@platform.com password
   ```

2. Check backend logs for authentication errors

### Database table not found

The tables are created automatically on backend startup. If they don't exist:
1. Restart the backend: `docker-compose restart backend`
2. Check logs: `docker-compose logs backend | grep -i "database initialized"`







