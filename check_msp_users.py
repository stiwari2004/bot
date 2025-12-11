from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
result = db.execute(text("""
    SELECT u.id, u.email, u.role, u.is_active, u.tenant_id, t.name, t.is_msp 
    FROM users u 
    LEFT JOIN tenants t ON u.tenant_id = t.id 
    WHERE u.role = 'admin' OR t.is_msp = true 
    ORDER BY u.id
"""))

print('=== ALL ADMIN/MSP USERS ===')
for row in result:
    print(f'ID: {row[0]}, Email: {row[1]}, Role: {row[2]}, Active: {row[3]}, Tenant ID: {row[4]}, Tenant: {row[5]}, is_msp: {row[6]}')

