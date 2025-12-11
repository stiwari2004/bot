# Tenant Separation Issues Found

## Problem
The `/admin` page is showing connections/data from the demo user (tenant_id=1) instead of being blank for new tenant admins.

## Root Cause
The `ConnectorController` is hardcoded to use `tenant_id = 1` (demo tenant) on line 64:
```python
def __init__(self, db: Session):
    self.db = db
    self.tenant_id = 1  # Demo tenant  <-- HARDCODED!
```

## Current Database State
- All infrastructure connections are for tenant_id = 1 (demo tenant)
- No connections exist for other tenants

## Endpoints That Need Fixing

### 1. `/api/v1/connectors/infrastructure-connections` (GET, POST, PUT, DELETE)
- **Current**: Uses `ConnectorController(db)` with hardcoded tenant_id=1
- **Should**: Use `get_current_user` to get tenant_id and pass to controller

### 2. `/api/v1/connectors/credentials` (GET, POST)
- **Current**: Uses `ConnectorController(db)` with hardcoded tenant_id=1
- **Should**: Use `get_current_user` to get tenant_id and pass to controller

### 3. Other endpoints that might have similar issues:
- Settings endpoints
- Ticketing connections (some already fixed, some still use tenant_id=1)

## Models That Have tenant_id (Good!)
- ✅ `InfrastructureConnection` - has tenant_id
- ✅ `Credential` - has tenant_id
- ✅ `TicketingToolConnection` - has tenant_id
- ✅ `MonitoringToolConnection` - has tenant_id

## Fix Required
1. Update `ConnectorController.__init__` to accept `tenant_id` parameter
2. Update all connectors endpoints to use `get_current_user` and pass tenant_id
3. Update frontend to use tenant-scoped endpoints (or ensure it's using the right endpoints)

