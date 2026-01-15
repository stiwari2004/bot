#!/bin/bash
# Check production container names

echo "=== All Production Containers ==="
docker ps -a --filter "name=bot-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== All Containers (bot-related) ==="
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -E "bot|postgres|redis" | head -20

echo ""
echo "=== Production Network Containers ==="
docker network inspect bot_app-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "Network not found"
