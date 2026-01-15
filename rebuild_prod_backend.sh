#!/bin/bash
# Rebuild production backend with latest code

set -e

echo "🔧 Rebuilding production backend..."

# 1. Build backend (this will pick up the latest code)
echo "1. Building backend image..."
docker-compose -f docker-compose.production.yml build --no-cache backend

# 2. Restart backend
echo ""
echo "2. Restarting backend..."
docker-compose -f docker-compose.production.yml up -d backend

# 3. Wait for backend to start
echo ""
echo "3. Waiting for backend to initialize..."
sleep 10

# 4. Check backend logs
echo ""
echo "4. Backend logs (last 20 lines):"
docker logs bot_backend_1 --tail=20 2>&1 | tail -20

# 5. Test super admin query
echo ""
echo "5. Testing super admin query..."
docker exec bot_backend_1 python -c "
from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from unittest.mock import Mock

db = SessionLocal()
try:
    # Test query
    admin = db.query(SuperAdmin).filter(SuperAdmin.email == 'admin@resolvify.tech').first()
    if admin:
        print(f'✅ Super admin found: {admin.email}')
        print(f'   ID: {admin.id}, Active: {admin.is_active}')
        # Test accessing attributes
        try:
            _ = admin.id
            _ = admin.email
            _ = admin.full_name
            print('✅ All attributes accessible')
        except Exception as e:
            print(f'❌ Error accessing attributes: {e}')
    else:
        print('❌ Super admin not found')
finally:
    db.close()
" 2>&1

echo ""
echo "✅ Backend rebuilt and restarted!"
echo ""
echo "Try logging in again at: https://admin.resolvify.tech/"
