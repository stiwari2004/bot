# Debugging Import Flow - Understanding the Problem

## What Actually Happens

### Step 1: Import super_admin_auth
```
from app.services.super_admin_auth import authenticate_super_admin
```

### Step 2: super_admin_auth.py executes imports (lines 18-25)
```python
from app.models import tenant_billing_config  # Imports MODULE
from app.models import tenant_subscription     # Imports MODULE  
from app.models import change_ticket          # Imports MODULE
from app.models import tenant                 # Imports MODULE
```

### Question: When `from app.models import tenant_billing_config` runs:
- Does it execute `models/__init__.py`? YES (because it's `from app.models import ...`)
- Does `models/__init__.py` import `TenantBillingConfig`? YES (line 15)
- Does that register the class? YES (when class definition executes)
- Then does it import `Tenant`? YES (line 30)

### But wait - there might be a problem:
When `models/__init__.py` is executed:
1. Line 15: `from app.models.tenant_billing_config import TenantBillingConfig` - registers TenantBillingConfig
2. Line 30: `from app.models.tenant import Tenant` - registers Tenant, which tries to configure mapper

But then in `super_admin_auth.py`:
3. Line 18: `from app.models import tenant_billing_config` - module already imported (cached)
4. Line 21: `from app.models import tenant` - module already imported (cached)

**The problem might be**: When `models/__init__.py` imports `Tenant` on line 30, it happens DURING the execution of `__init__.py`. At that point, `TenantBillingConfig` is already registered. So why does it fail?

Unless... the error happens when we QUERY, not when we import. When we query `SuperAdmin`, SQLAlchemy configures ALL mappers, including `Tenant`. At that point, it looks for `TenantBillingConfig` in the registry.

So the question is: Is `TenantBillingConfig` actually in the registry when we query?

Maybe the issue is that we're importing `Tenant` in `models/__init__.py`, but `TenantBillingConfig` isn't actually registered properly because of how the imports are structured?
