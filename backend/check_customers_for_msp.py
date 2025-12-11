#!/usr/bin/env python3
"""Check customers (sub-tenants) for MSPs"""
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()

print("=" * 80)
print("MSP TENANTS:")
print("=" * 80)
result = conn.execute(text("""
    SELECT id, name, is_msp, parent_tenant_id
    FROM tenants
    WHERE is_msp = True
    ORDER BY id
"""))
msp_tenants = result.fetchall()
for r in msp_tenants:
    print(f"MSP ID: {r[0]}, Name: {r[1]}, is_msp: {r[2]}, parent: {r[3]}")

print("\n" + "=" * 80)
print("CUSTOMER TENANTS (sub-tenants with parent_tenant_id):")
print("=" * 80)
result = conn.execute(text("""
    SELECT id, name, is_msp, parent_tenant_id
    FROM tenants
    WHERE parent_tenant_id IS NOT NULL
    ORDER BY parent_tenant_id, id
"""))
customer_tenants = result.fetchall()
if customer_tenants:
    for r in customer_tenants:
        print(f"Customer ID: {r[0]}, Name: {r[1]}, is_msp: {r[2]}, parent_tenant_id: {r[3]}")
else:
    print("NO CUSTOMER TENANTS FOUND!")

print("\n" + "=" * 80)
print("CHECKING admin@client32.com DETAILS:")
print("=" * 80)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id, 
           t.id as tenant_id, t.name as tenant_name, t.is_msp, t.parent_tenant_id
    FROM users u 
    JOIN tenants t ON u.tenant_id = t.id 
    WHERE u.email = 'admin@client32.com'
"""))
row = result.fetchone()
if row:
    print(f"User ID: {row[0]}")
    print(f"Email: {row[1]}")
    print(f"Role: {row[2]}")
    print(f"Tenant ID: {row[3]}")
    print(f"Tenant Name: {row[5]}")
    print(f"Tenant is_msp: {row[6]}")
    print(f"Tenant parent_tenant_id: {row[7]}")
    print()
    if row[6]:  # is_msp
        print("❌ PROBLEM: User is in an MSP tenant, not a customer tenant!")
        print("   This user should be in a customer tenant (sub-tenant with parent_tenant_id)")
    else:
        print("✅ User is in a customer tenant (correct)")

conn.close()

