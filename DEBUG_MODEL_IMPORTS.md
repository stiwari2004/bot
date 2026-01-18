# Debugging SQLAlchemy Model Import Order Issue

## The Problem
When querying `SuperAdmin`, SQLAlchemy fails with:
```
When initializing mapper Mapper[Ticket(tickets)], expression 'Tenant' failed to locate a name ('Tenant')
```

## What's Happening

1. We query `SuperAdmin`
2. SQLAlchemy tries to configure ALL models in the registry
3. When configuring `Ticket`, it tries to resolve `relationship("Tenant", ...)`
4. `Tenant` is not found in the registry at that moment

## Key Question
**Why is Tenant not in the registry when Ticket's mapper is being configured?**

We import Tenant BEFORE Ticket in `models/__init__.py`, so Tenant should be registered first.

## Possible Causes

1. **Import path issue**: Something is importing Ticket before models/__init__.py runs
2. **Circular import**: Some circular dependency causing models to load in wrong order
3. **Lazy registration**: Tenant is imported but not registered with Base yet
4. **Registry not initialized**: The Base registry isn't seeing Tenant when Ticket is configured

## What We Need to Check

1. What's the actual import order when `super_admin_auth.py` runs?
2. Is Tenant actually registered with Base when Ticket is imported?
3. Are there any circular imports between models?
4. Does importing `app.models` actually execute the imports in __init__.py?

## Hypothesis
Maybe when we directly import `from app.models.super_admin import SuperAdmin`, it doesn't trigger `models/__init__.py`, and then when SQLAlchemy tries to configure models, Ticket is in the registry but Tenant isn't (because __init__.py didn't run).

But we added `import app.models` to `super_admin_auth.py` to fix this... so why isn't it working?
