#!/bin/bash
# Fix production network connectivity

set -e

echo "🔧 Fixing production network connectivity..."

# 1. Check if containers are on the network
echo "1. Checking network membership..."
docker network inspect bot_app-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "Network not found"

# 2. Check production containers
echo ""
echo "2. Production containers:"
docker ps -a --filter "name=bot-prod" --format "table {{.Names}}\t{{.Status}}"

# 3. Check if backend can reach postgres
echo ""
echo "3. Testing network connectivity..."
docker exec bot-prod_backend_1 python -c "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('postgres', 5432)); s.close(); print('✅ Postgres reachable' if result == 0 else '❌ Cannot reach postgres')" 2>&1 || echo "Backend container not running"

# 4. Restart production services to ensure they're on the network
echo ""
echo "4. Restarting production services to fix network..."
docker-compose -f docker-compose.production.yml -p bot-prod down
docker-compose -f docker-compose.production.yml -p bot-prod up -d

# 5. Wait for services to start
echo ""
echo "5. Waiting for services to initialize..."
sleep 10

# 6. Check backend logs
echo ""
echo "6. Backend logs (checking for DB connection):"
docker logs bot-prod_backend_1 --tail=20 2>&1 | grep -i -E "database|postgres|connected|error" || echo "No recent DB-related logs"

echo ""
echo "✅ Done! Check if backend can now connect to postgres."
