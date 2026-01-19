#!/bin/bash
# Check for container naming conflicts between production and dev

echo "🔍 Checking container conflicts..."

echo ""
echo "📋 Production containers (from docker-compose.production.yml):"
docker-compose -f docker-compose.production.yml ps 2>/dev/null || echo "Production not running"

echo ""
echo "📋 Dev containers (from docker-compose.dev.yml):"
docker-compose -f docker-compose.dev.yml ps 2>/dev/null || echo "Dev not running"

echo ""
echo "📋 All containers with 'bot' in name:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -i bot || echo "No bot containers found"

echo ""
echo "📋 Containers that might conflict:"
docker ps -a --format "{{.Names}}" | grep -E "bot_postgres|bot_redis|bot_backend|bot_frontend|bot_worker" | sort
