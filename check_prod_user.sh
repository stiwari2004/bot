#!/bin/bash
# Check production user and authentication

echo "=== 1. Check if demo user exists ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, is_active, tenant_id FROM users WHERE email = 'demo@example.com';" 2>&1

echo ""
echo "=== 2. Check all users ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, is_active, tenant_id FROM users LIMIT 10;" 2>&1

echo ""
echo "=== 3. Check super_admins ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, is_active FROM super_admins LIMIT 10;" 2>&1

echo ""
echo "=== 4. Check user_sessions table ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, user_id, expires_at, is_revoked FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE email = 'demo@example.com') ORDER BY created_at DESC LIMIT 5;" 2>&1

echo ""
echo "=== 5. Test backend can query user ==="
docker exec bot-prod_backend_1 python -c "
from app.core.database import SessionLocal
from app.models.user import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'demo@example.com').first()
if user:
    print(f'✅ User found: {user.email}, active: {user.is_active}, tenant: {user.tenant_id}')
else:
    print('❌ User not found')
db.close()
" 2>&1
