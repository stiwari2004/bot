#!/bin/bash
# Quick diagnostic script to check container status

echo "=== Container Status ==="
docker ps -a --filter "name=bot-dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Backend Logs (last 100 lines) ==="
docker logs bot-dev-backend --tail=100 2>&1 || echo "Container not found or not running"

echo ""
echo "=== Postgres Logs (last 50 lines) ==="
docker logs bot-dev-postgres --tail=50 2>&1 || echo "Container not found or not running"

echo ""
echo "=== Redis Logs (last 50 lines) ==="
docker logs bot-dev-redis --tail=50 2>&1 || echo "Container not found or not running"

echo ""
echo "=== Network Status ==="
docker network ls | grep bot

echo ""
echo "=== Backend Container Health ==="
docker inspect bot-dev-backend --format='{{.State.Status}} - {{.State.Health.Status}}' 2>/dev/null || echo "Container not found"
