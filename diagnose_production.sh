#!/bin/bash
# Diagnose production environment issues

echo "🔍 Diagnosing production environment..."

echo ""
echo "📋 Production container status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "📋 Production backend health:"
curl -s http://localhost:8000/health | jq . || curl -s http://localhost:8000/health

echo ""
echo "📋 Production backend logs (last 30 lines):"
docker-compose -f docker-compose.production.yml logs --tail=30 backend

echo ""
echo "📋 Production database connectivity:"
docker exec -it bot-prod-backend python -c "
from app.core.database import SessionLocal
try:
    db = SessionLocal()
    result = db.execute('SELECT 1').scalar()
    print('✅ Database connection: OK')
    db.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
" 2>/dev/null || echo "Could not test database connection"

echo ""
echo "📋 Production frontend status:"
docker-compose -f docker-compose.production.yml logs --tail=20 frontend | tail -10

echo ""
echo "📋 Production proxy status:"
docker-compose -f docker-compose.production.yml logs --tail=20 proxy | tail -10
