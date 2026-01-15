#!/bin/bash
# Diagnose super admin session issue

echo "=== 1. Check Super Admin in Database ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, email, is_active, last_login, created_at, updated_at 
FROM super_admins 
ORDER BY id;
"

echo ""
echo "=== 2. Check Recent Backend Logs (super admin related) ==="
docker logs bot-prod_backend_1 --tail=50 2>&1 | grep -i -E "super.admin|super_admin|ObjectDeleted|session|database" | tail -15

echo ""
echo "=== 3. Test Super Admin Query from Backend ==="
docker exec bot-prod_backend_1 python -c "
from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin

db = SessionLocal()
try:
    admins = db.query(SuperAdmin).all()
    print(f'Found {len(admins)} super admins:')
    for admin in admins:
        print(f'  - ID: {admin.id}, Email: {admin.email}, Active: {admin.is_active}')
        # Try to access attributes
        try:
            print(f'    Last login: {admin.last_login}')
            print(f'    Full name: {admin.full_name}')
        except Exception as e:
            print(f'    Error accessing attributes: {e}')
finally:
    db.close()
" 2>&1

echo ""
echo "=== 4. Check Database Connection Pool ==="
docker logs bot-prod_backend_1 --tail=30 2>&1 | grep -i -E "connection|pool|timeout" | tail -5
