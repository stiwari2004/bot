#!/bin/bash
# Check production services status

echo "=== Production Container Status ==="
docker ps -a --filter "name=bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -v "bot-dev"

echo ""
echo "=== Production Network ==="
docker network inspect bot_app-network --format 'Name: {{.Name}}
Containers: {{len .Containers}}' 2>/dev/null || echo "Network not found"

echo ""
echo "=== Production Backend Logs (last 20 lines) ==="
docker logs bot-backend --tail=20 2>/dev/null || echo "Backend container not found"

echo ""
echo "=== Production Postgres Status ==="
docker ps -a --filter "name=postgres" --format "table {{.Names}}\t{{.Status}}" | grep -v "bot-dev"
