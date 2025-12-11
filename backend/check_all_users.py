#!/usr/bin/env python3
"""Check all users and their roles"""
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()

print("=" * 80)
print("ALL USERS WITH THEIR ROLES AND TENANTS:")
print("=" * 80)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id, u.is_active,
           t.name as tenant_name, t.is_msp, t.parent_tenant_id
    FROM users u 
    JOIN tenants t ON u.tenant_id = t.id 
    ORDER BY u.id
"""))
rows = result.fetchall()
for r in rows:
    print(f"ID: {r[0]:2d} | Email: {r[1]:25s} | Role: {r[2]:15s} | Tenant: {r[5]:15s} | is_msp: {r[6]} | parent: {r[7]}")
    print(f"     Active: {r[4]}")
    print()

print("=" * 80)
print("USERS BY ROLE:")
print("=" * 80)
result = conn.execute(text("""
    SELECT role, COUNT(*) as count
    FROM users
    GROUP BY role
    ORDER BY role
"""))
rows = result.fetchall()
for r in rows:
    print(f"Role '{r[0]}': {r[1]} users")

print("\n" + "=" * 80)
print("CHECKING admin@client32.com:")
print("=" * 80)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id, u.is_active,
           t.name as tenant_name, t.is_msp, t.parent_tenant_id
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
    print(f"Tenant Name: {row[4]}")
    print(f"Tenant is_msp: {row[6]}")
    print(f"Tenant parent_tenant_id: {row[7]}")
    print(f"Is Active: {row[5]}")
else:
    print("User not found!")

conn.close()

