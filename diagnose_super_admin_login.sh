#!/bin/bash
# Diagnose super admin login issue

echo "=========================================="
echo "Super Admin Login Diagnosis"
echo "=========================================="
echo ""

echo "1. Check if super admin exists in dev database..."
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "
SELECT id, email, is_active, 
       CASE WHEN password_hash IS NULL THEN 'NULL' 
            ELSE substring(password_hash, 1, 30) || '...' 
       END as password_hash_preview
FROM super_admins 
WHERE email ILIKE '%admin%' OR email ILIKE '%dev%';
"

echo ""
echo "2. Test super admin login directly from backend container..."
docker exec bot-dev-backend python -c "
import sys
sys.path.insert(0, '/app')
from app.services.super_admin_auth import authenticate_super_admin
from app.core.database import SessionLocal

db = SessionLocal()
email = 'admin@dev.resolvify.tech'
password = 'S@ndyDemo#2025!'  # Change this to the actual password you're using

result = authenticate_super_admin(db, email, password)
if result:
    print(f'✅ Login successful for {email}')
else:
    print(f'❌ Login failed for {email}')
    print('   Check if password is correct or if user exists')
    
db.close()
"

echo ""
echo "3. Check backend logs for login attempts..."
docker-compose -f docker-compose.dev.yml logs backend --tail=30 | grep -i "super.*admin\|login\|401\|unauthorized" || echo "No recent login logs"

echo ""
echo "=========================================="
