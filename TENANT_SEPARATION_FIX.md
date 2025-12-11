# Tenant Separation Fix - Connectors Endpoints

## Problem
Users from tenant_id=6, 7, etc. were seeing infrastructure connections and credentials that belong to tenant_id=1 (demo user) in the `/admin` settings page.

## Root Cause
The `/api/v1/connectors/*` endpoints were using `ConnectorController(db)` with a hardcoded `tenant_id = 1`, so all queries returned data for the demo tenant regardless of which user was logged in.

## Fix Applied

### 1. Updated `ConnectorController` (backend/app/controllers/connector_controller.py)
- Changed `__init__` to accept `tenant_id` parameter (defaults to 1 for backward compatibility)
- All controller methods already use `self.tenant_id` for filtering, so no changes needed there

### 2. Updated Connectors Endpoints (backend/app/api/v1/endpoints/connectors.py)
Added `get_current_user` dependency to all endpoints and pass `tenant_id` to controller:

- ✅ `POST /credentials` - Now uses current user's tenant_id
- ✅ `GET /credentials` - Now filters by current user's tenant_id
- ✅ `POST /infrastructure-connections` - Now uses current user's tenant_id
- ✅ `GET /infrastructure-connections` - Now filters by current user's tenant_id
- ✅ `PUT /infrastructure-connections/{id}` - Now verifies tenant ownership
- ✅ `DELETE /infrastructure-connections/{id}` - Now verifies tenant ownership
- ✅ `POST /infrastructure-connections/{id}/test` - Now verifies tenant ownership
- ✅ `GET /infrastructure-connections/{id}/discover` - Now verifies tenant ownership
- ✅ `POST /infrastructure-connections/{id}/save-discovered` - Now uses current user's tenant_id
- ✅ `POST /infrastructure-connections/{id}/test-command` - Now verifies tenant ownership

## Verification
The controller methods use:
- `get_by_id_and_tenant()` - Verifies connection belongs to tenant
- `get_by_tenant()` - Filters by tenant_id
- Service methods receive `tenant_id` parameter

## Result
Now when a user from tenant_id=6 or tenant_id=7 logs into `/admin`:
- They will see an empty list of connections (if they haven't created any)
- They can only create/view/modify connections for their own tenant
- They cannot see or access connections from tenant_id=1 (demo) or any other tenant

## Testing
1. Log in as user from tenant_id=6 → Should see empty connections list
2. Create a connection → Should be saved with tenant_id=6
3. Log in as user from tenant_id=1 → Should only see connections for tenant_id=1
4. Try to access connection from tenant_id=6 → Should get 404/403 error

