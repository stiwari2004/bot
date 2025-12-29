#!/bin/bash
# Script to fix super-admin endpoints and create super admin user if needed

set -e

echo "🔧 Fixing Super Admin Endpoints"
echo "================================"
echo ""

# Step 1: Pull latest code
echo "📥 Step 1: Pulling latest code..."
cd "$(dirname "$0")/.." || exit 1
git pull origin main || echo "⚠️  Warning: git pull failed (may not be in git repo)"
echo "✅ Code updated"
echo ""

# Step 2: Check if backend container is running
echo "🐳 Step 2: Checking Docker containers..."
if ! docker ps | grep -q "bot_backend"; then
    echo "❌ Backend container is not running!"
    echo "   Starting backend container..."
    docker-compose -f docker-compose.production.yml up -d backend
    echo "   ⏳ Waiting for backend to start..."
    sleep 10
else
    echo "✅ Backend container is running"
fi
echo ""

# Step 3: Restart backend to load new endpoints
echo "🔄 Step 3: Restarting backend to load new endpoints..."
docker-compose -f docker-compose.production.yml restart backend
echo "⏳ Waiting for backend to restart..."
sleep 15
echo "✅ Backend restarted"
echo ""

# Step 4: Check if super admin exists
echo "👤 Step 4: Checking for super admin user..."
echo "   Running check inside backend container..."

# Check if super admin exists
SUPER_ADMIN_EXISTS=$(docker-compose -f docker-compose.production.yml exec -T backend python -c "
from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
import asyncio

async def check():
    await init_db()
    db = SessionLocal()
    try:
        admin = db.query(SuperAdmin).first()
        if admin:
            print('EXISTS')
            print(f'Email: {admin.email}')
        else:
            print('NOT_EXISTS')
    finally:
        db.close()

asyncio.run(check())
" 2>/dev/null || echo "ERROR")

if echo "$SUPER_ADMIN_EXISTS" | grep -q "EXISTS"; then
    echo "✅ Super admin user exists"
    echo "$SUPER_ADMIN_EXISTS" | grep "Email:" || true
elif echo "$SUPER_ADMIN_EXISTS" | grep -q "NOT_EXISTS"; then
    echo "⚠️  No super admin user found"
    echo ""
    echo "📝 To create a super admin user, run:"
    echo "   docker-compose -f docker-compose.production.yml exec backend python scripts/create_super_admin.py <email> <password> [full_name]"
    echo ""
    echo "   Example:"
    echo "   docker-compose -f docker-compose.production.yml exec backend python scripts/create_super_admin.py admin@resolvify.tech admin123 \"Super Admin\""
else
    echo "⚠️  Could not check super admin status (backend may still be starting)"
fi
echo ""

# Step 5: Check if endpoints are registered
echo "🔍 Step 5: Checking if endpoints are registered..."
echo "   Testing /api/v1/super-admin/overview endpoint..."

# Wait a bit more for backend to fully start
sleep 5

# Test endpoint (will fail if not authenticated, but 404 means endpoint doesn't exist)
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/super-admin/overview 2>/dev/null || echo "000")

if [ "$RESPONSE" = "401" ]; then
    echo "✅ Endpoint is registered (401 = authentication required, which is expected)"
elif [ "$RESPONSE" = "404" ]; then
    echo "❌ Endpoint not found (404) - backend may need more time to start or there's an import error"
    echo "   Check backend logs: docker-compose -f docker-compose.production.yml logs backend | tail -50"
elif [ "$RESPONSE" = "000" ]; then
    echo "⚠️  Could not connect to backend (backend may still be starting)"
    echo "   Check backend status: docker-compose -f docker-compose.production.yml ps backend"
else
    echo "⚠️  Unexpected response code: $RESPONSE"
fi
echo ""

# Step 6: Show backend logs for any errors
echo "📋 Step 6: Recent backend logs (last 20 lines)..."
echo "   (Look for any import errors or super-admin related messages)"
docker-compose -f docker-compose.production.yml logs --tail=20 backend | grep -i "super\|error\|import" || echo "   No relevant errors found"
echo ""

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. If super admin doesn't exist, create one using the command shown above"
echo "   2. Try logging in at https://admin.resolvify.tech"
echo "   3. If endpoints still return 404, check backend logs for import errors:"
echo "      docker-compose -f docker-compose.production.yml logs backend | grep -i error"
echo ""



