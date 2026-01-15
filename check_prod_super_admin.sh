#!/bin/bash
# Check production super admin with correct container names

echo "=== 1. Check Super Admin in Production Database ==="
docker exec bot_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, email, is_active, last_login, created_at 
FROM super_admins 
ORDER BY id;
"

echo ""
echo "=== 2. Check Production Backend Logs (super admin related) ==="
docker logs bot_backend_1 --tail=50 2>&1 | grep -i -E "super.admin|super_admin|ObjectDeleted|session" | tail -15

echo ""
echo "=== 3. Test Super Admin Query ==="
docker exec bot_backend_1 python -c "
from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin

db = SessionLocal()
try:
    admins = db.query(SuperAdmin).all()
    print(f'Found {len(admins)} super admins:')
    for admin in admins:
        print(f'  - ID: {admin.id}, Email: {admin.email}, Active: {admin.is_active}')
finally:
    db.close()
" 2>&1
