# License Plan System Implementation Summary

## Overview
Extended the existing subscription system to support **license plans** with **feature-based access control**. This allows you to define subscription tiers (Free, Starter, Professional, Enterprise) with specific feature sets, and automatically enforce access based on the tenant's active license plan.

## What's Been Implemented

### 1. Database Models

#### `LicensePlan` Model (`backend/app/models/license_plan.py`)
- Defines subscription plans with feature flags
- Fields:
  - `plan_key`: Unique identifier (e.g., "free", "starter", "professional", "enterprise")
  - `plan_name`: Display name
  - `description`: Plan description
  - `default_max_seats`, `default_max_nodes`: Default limits
  - `default_monthly_price`: Default pricing
  - `features`: JSON object with feature flags (e.g., `{"solarwinds": true, "rbac_custom_roles": false}`)
  - `is_system_plan`: True for predefined plans (cannot be deleted)
  - `is_custom`: True for custom plans created by super admin

#### Updated `TenantSubscription` Model
- Added `license_plan_id` foreign key to link subscriptions to license plans
- Relationship to `LicensePlan` model

### 2. License Service (`backend/app/services/license_service.py`)

**Key Methods:**
- `has_feature(tenant_id, feature_name)`: Check if tenant has access to a feature
- `get_available_features(tenant_id)`: Get all available features for a tenant
- `get_license_plan(tenant_id)`: Get the license plan for a tenant
- `initialize_default_plans(db)`: Initialize default plans (Free, Starter, Professional, Enterprise)

**Available Features:**
- RBAC: `rbac_basic`, `rbac_custom_roles`, `rbac_permissions`
- Integrations: `servicenow`, `zoho`, `manageengine`, `solarwinds`, `datadog`, `prometheus`, `azure_monitor`, `splunk`
- Advanced: `advanced_analytics`, `api_access`, `webhook_access`, `bulk_operations`, `activity_logging`, `two_factor_auth`
- Enterprise: `white_labeling`, `on_premise`, `priority_support`, `sla_guarantees`, `custom_integrations`

### 3. License Middleware (`backend/app/middleware/license_middleware.py`)

**Decorators:**
- `@require_license_feature(feature_name)`: Require a specific feature
- `@require_any_license_feature(*feature_names)`: Require any one of the specified features

**Usage:**
```python
@router.get("/solarwinds/alerts")
@require_license_feature("solarwinds")
async def get_solarwinds_alerts(...):
    ...
```

### 4. API Endpoints (`backend/app/api/v1/endpoints/license_plans.py`)

**Super Admin Only:**
- `GET /api/v1/license-plans`: List all license plans
- `GET /api/v1/license-plans/{plan_id}`: Get a specific plan
- `POST /api/v1/license-plans`: Create a custom license plan
- `PUT /api/v1/license-plans/{plan_id}`: Update a license plan (custom only)
- `POST /api/v1/license-plans/initialize`: Initialize default plans
- `GET /api/v1/license-plans/features/list`: List all available features

### 5. Updated Subscription Endpoints

**Enhanced `SubscriptionCreate` and `SubscriptionUpdate`:**
- Added `license_plan_id` field
- If `license_plan_id` is provided, automatically uses plan defaults for `max_seats`, `max_nodes`, and `monthly_price`
- `SubscriptionResponse` now includes `license_plan_id` and `license_plan_name`

## Default License Plans

### Free
- **Seats**: 3
- **Nodes**: 5
- **Features**: ServiceNow only, no RBAC, no API access

### Starter
- **Seats**: 10
- **Nodes**: 20
- **Features**: Multiple ticketing/monitoring integrations, basic RBAC, API access

### Professional
- **Seats**: 50
- **Nodes**: 100
- **Features**: All integrations (including SolarWinds), full RBAC, advanced analytics, bulk operations

### Enterprise
- **Seats**: Unlimited
- **Nodes**: Unlimited
- **Features**: All features enabled (white-labeling, on-premise, custom integrations, etc.)

## How to Use

### 1. Initialize Default Plans
```bash
POST /api/v1/license-plans/initialize
```
This creates the 4 default plans (Free, Starter, Professional, Enterprise).

### 2. Create Subscription with License Plan
```json
POST /api/v1/subscriptions/subscriptions
{
  "tenant_id": 1,
  "license_plan_id": 2,  // Starter plan
  "is_enforced": true
}
```
This automatically sets:
- `max_seats` = 10 (from plan)
- `max_nodes` = 20 (from plan)
- `monthly_price` = 99 (from plan)

### 3. Check Feature Access in Code
```python
from app.services.license_service import LicenseService

# In an endpoint or service
has_solarwinds = LicenseService.has_feature(db, tenant_id, "solarwinds")
if not has_solarwinds:
    raise HTTPException(403, "SolarWinds not available in your plan")
```

### 4. Protect Endpoints with Middleware
```python
from app.middleware.license_middleware import require_license_feature

@router.get("/solarwinds/alerts")
@require_license_feature("solarwinds")
async def get_solarwinds_alerts(...):
    ...
```

## Next Steps

1. **Apply License Checks to Existing Endpoints:**
   - SolarWinds endpoints: `require_license_feature("solarwinds")`
   - RBAC custom roles: `require_license_feature("rbac_custom_roles")`
   - Advanced analytics: `require_license_feature("advanced_analytics")`
   - API endpoints: `require_license_feature("api_access")`

2. **Frontend Integration:**
   - Show license plan in subscription management UI
   - Display available features per plan
   - Show upgrade prompts when feature is not available
   - Feature comparison table

3. **Usage Tracking:**
   - Track feature usage per tenant
   - Generate reports on feature adoption
   - Identify upsell opportunities

4. **Automatic Plan Assignment:**
   - Auto-assign Free plan to new tenants
   - Suggest plan upgrades based on usage

## Database Migration

The new `license_plans` table will be created automatically when you run the application. To initialize default plans, call:

```python
from app.services.license_service import LicenseService
from app.core.database import SessionLocal

db = SessionLocal()
LicenseService.initialize_default_plans(db)
db.close()
```

Or use the API endpoint: `POST /api/v1/license-plans/initialize`

## Benefits

1. **Flexible**: Define custom plans with any feature combination
2. **Automatic**: Plan defaults applied when creating subscriptions
3. **Enforced**: Middleware automatically blocks unauthorized access
4. **Extensible**: Easy to add new features and plans
5. **Integrated**: Works seamlessly with existing subscription system



