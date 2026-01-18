#!/usr/bin/env python3
"""
Test what models are actually registered in SQLAlchemy Base registry
"""
import sys
sys.path.insert(0, '/app')

# Check Base registry before importing models
from app.core.database import Base
print("Before importing models:")
print(f"  Base.registry._class_registry keys: {list(Base.registry._class_registry.keys())}")

# Import models/__init__.py
print("\nImporting models/__init__.py...")
from app.models import Tenant, TenantBillingConfig

print("After importing models:")
print(f"  Base.registry._class_registry keys: {list(Base.registry._class_registry.keys())}")

# Check specifically for TenantBillingConfig
if 'TenantBillingConfig' in Base.registry._class_registry:
    print("\n✅ TenantBillingConfig is in registry")
else:
    print("\n❌ TenantBillingConfig is NOT in registry!")

# Check what's actually there
print("\nAll registered classes:")
for name, cls in Base.registry._class_registry.items():
    print(f"  {name}: {cls}")
