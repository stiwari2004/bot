#!/bin/bash
# Check production backend database connectivity

echo "=== Production Backend Container ==="
docker ps -a --filter "name=bot-prod_backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Production Backend Logs (last 50 lines) ==="
docker logs bot-prod_backend_1 --tail=50 2>&1 | grep -i -E "database|postgres|connection|error|failed|authentication|auth"

echo ""
echo "=== Test DB Connection from Production Backend ==="
docker exec bot-prod_backend_1 python -c "from sqlalchemy import text; from app.core.database import SessionLocal; db = SessionLocal(); db.execute(text('SELECT 1')); print('✅ DB OK'); db.close()" 2>&1

echo ""
echo "=== Check if backend can reach postgres ==="
docker exec bot-prod_backend_1 python -c "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('postgres', 5432)); s.close(); print('✅ Postgres reachable' if result == 0 else '❌ Cannot reach postgres')" 2>&1

echo ""
echo "=== Production Postgres Status ==="
docker ps -a --filter "name=bot-prod_postgres" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "=== Check Production Network ==="
docker network inspect bot_app-network --format 'Containers: {{len .Containers}}' 2>/dev/null
