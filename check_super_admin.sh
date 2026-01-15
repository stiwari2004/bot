#!/bin/bash
# Check super admin authentication

echo "=== 1. Check Super Admins in Database ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, is_active, last_login FROM super_admins;" 2>&1

echo ""
echo "=== 2. Check Super Admin Login Logs ==="
docker logs bot-prod_backend_1 --tail=100 2>&1 | grep -i -E "super.admin|super_admin|admin@|401|unauthorized" | tail -20

echo ""
echo "=== 3. Test Super Admin Authentication from Backend ==="
docker exec bot-prod_backend_1 python -c "
from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import authenticate_super_admin

db = SessionLocal()
try:
    # Check if super admin exists
    admins = db.query(SuperAdmin).all()
    print(f'Found {len(admins)} super admins:')
    for admin in admins:
        print(f'  - {admin.email} (active: {admin.is_active})')
    
    # Try authentication (replace with actual credentials)
    if admins:
        test_email = admins[0].email
        print(f'\nTesting authentication for: {test_email}')
        # Note: This will fail without correct password, but shows if function works
        result = authenticate_super_admin(db, test_email, 'wrong_password')
        if result:
            print('✅ Authentication function works')
        else:
            print('❌ Authentication failed (expected with wrong password)')
finally:
    db.close()
" 2>&1

echo ""
echo "=== 4. Check Database Connection Pool ==="
docker logs bot-prod_backend_1 --tail=50 2>&1 | grep -i -E "connection|pool|database|postgres" | tail -10

echo ""
echo "=== 5. Check Recent Errors ==="
docker logs bot-prod_backend_1 --tail=50 2>&1 | grep -i "error" | tail -10
