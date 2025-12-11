#!/usr/bin/env python3
"""Check user and tenant data"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()

# Check the specific user
print("=" * 60)
print("Checking user: admin@client31.com")
print("=" * 60)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id, 
           t.name as tenant_name, t.is_msp, t.parent_tenant_id
    FROM users u 
    JOIN tenants t ON u.tenant_id = t.id 
    WHERE u.email = 'admin@client31.com'
"""))
row = result.fetchone()
if row:
    print(f"User ID: {row[0]}")
    print(f"Email: {row[1]}")
    print(f"Role: {row[2]}")
    print(f"Tenant ID: {row[3]}")
    print(f"Tenant Name: {row[4]}")
    print(f"Tenant is_msp: {row[5]}")
    print(f"Parent Tenant ID: {row[6]}")
else:
    print("User not found!")

print("\n" + "=" * 60)
print("All Tenants:")
print("=" * 60)
result = conn.execute(text("""
    SELECT id, name, is_msp, parent_tenant_id 
    FROM tenants 
    ORDER BY id
"""))
rows = result.fetchall()
for r in rows:
    print(f"ID: {r[0]}, Name: {r[1]}, is_msp: {r[2]}, parent_tenant_id: {r[3]}")

print("\n" + "=" * 60)
print("All Admin Users:")
print("=" * 60)
result = conn.execute(text("""
    SELECT u.id, u.email, u.role, u.tenant_id, 
           t.name as tenant_name, t.is_msp
    FROM users u 
    JOIN tenants t ON u.tenant_id = t.id 
    WHERE u.role = 'admin'
    ORDER BY u.id
"""))
rows = result.fetchall()
for r in rows:
    print(f"User: {r[1]}, Role: {r[2]}, Tenant: {r[4]} (is_msp: {r[5]})")

conn.close()

