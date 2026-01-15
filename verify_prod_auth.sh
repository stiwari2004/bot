#!/bin/bash
# Verify production authentication setup

echo "=== 1. Test Production Backend DB Connection ==="
docker exec bot-prod_backend_1 python -c "from sqlalchemy import text; from app.core.database import SessionLocal; db = SessionLocal(); db.execute(text('SELECT 1')); print('✅ DB Connection OK'); db.close()" 2>&1

echo ""
echo "=== 2. Check if Users Table Exists ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as user_count FROM users;" 2>&1

echo ""
echo "=== 3. Check if Super Admins Table Exists ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as admin_count FROM super_admins;" 2>&1

echo ""
echo "=== 4. Check Demo User ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, is_active FROM users WHERE email LIKE '%demo%' OR email LIKE '%admin%' LIMIT 5;" 2>&1

echo ""
echo "=== 5. Check Super Admins ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, email, is_active FROM super_admins LIMIT 5;" 2>&1

echo ""
echo "=== 6. Production Backend Logs (auth-related) ==="
docker logs bot-prod_backend_1 --tail=50 2>&1 | grep -i -E "auth|login|database|postgres|error" | tail -10
