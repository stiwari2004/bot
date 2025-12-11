#!/usr/bin/env python3
"""Check customers (sub-tenants) for MSPs"""
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()

print("=" * 60)
print("Checking customers (sub-tenants) for MSP tenant 'client3' (ID: 5):")
print("=" * 60)
result = conn.execute(text("""
    SELECT id, name, is_msp, parent_tenant_id 
    FROM tenants 
    WHERE parent_tenant_id = 5
    ORDER BY id
"""))
rows = result.fetchall()
if rows:
    for r in rows:
        print(f"Customer ID: {r[0]}, Name: {r[1]}, is_msp: {r[2]}, parent_tenant_id: {r[3]}")
else:
    print("No customers found for tenant ID 5 (client3)")

print("\n" + "=" * 60)
print("All tenants with parent_tenant_id (sub-tenants):")
print("=" * 60)
result = conn.execute(text("""
    SELECT id, name, is_msp, parent_tenant_id 
    FROM tenants 
    WHERE parent_tenant_id IS NOT NULL
    ORDER BY parent_tenant_id, id
"""))
rows = result.fetchall()
if rows:
    for r in rows:
        print(f"ID: {r[0]}, Name: {r[1]}, is_msp: {r[2]}, parent_tenant_id: {r[3]}")
else:
    print("No sub-tenants found")

print("\n" + "=" * 60)
print("Users in tenant 'client3' (ID: 5):")
print("=" * 60)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id
    FROM users u 
    WHERE u.tenant_id = 5
    ORDER BY u.id
"""))
rows = result.fetchall()
for r in rows:
    print(f"User ID: {r[0]}, Email: {r[1]}, Role: {r[2]}, Tenant ID: {r[3]}")

conn.close()

