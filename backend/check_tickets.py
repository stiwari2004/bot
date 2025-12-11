#!/usr/bin/env python3
"""Quick script to check tickets in database"""
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Check tickets
result = db.execute(text('SELECT id, title, tenant_id, source, status FROM tickets ORDER BY id LIMIT 20'))
tickets = result.fetchall()
print(f'\n=== First 20 Tickets ===')
for t in tickets:
    print(f'ID: {t[0]}, Title: {t[1][:60] if t[1] else "N/A"}, Tenant: {t[2]}, Source: {t[3]}, Status: {t[4]}')

# Check by tenant and source
result = db.execute(text('SELECT tenant_id, source, COUNT(*) as count FROM tickets GROUP BY tenant_id, source ORDER BY tenant_id, source'))
groups = result.fetchall()
print(f'\n=== Tickets by Tenant and Source ===')
for g in groups:
    print(f'Tenant {g[0]}, Source: {g[1]}, Count: {g[2]}')

# Check demo user
result = db.execute(text('SELECT id, email, tenant_id, role FROM users WHERE email = \'demo@example.com\''))
user = result.fetchone()
if user:
    print(f'\n=== Demo User ===')
    print(f'ID: {user[0]}, Email: {user[1]}, Tenant: {user[2]}, Role: {user[3]}')
    print(f'\nTickets for tenant {user[2]}:')
    result = db.execute(text(f'SELECT COUNT(*) FROM tickets WHERE tenant_id = {user[2]}'))
    count = result.fetchone()[0]
    print(f'Total: {count} tickets')

db.close()

