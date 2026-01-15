#!/bin/bash
# Start dev services

set -e

echo "🔧 Starting dev services..."

# 1. Check current dev container status
echo "1. Checking current dev containers..."
docker ps -a --filter "name=bot-dev" --format "table {{.Names}}\t{{.Status}}"

# 2. Start dev services with explicit project name
echo ""
echo "2. Starting dev services..."
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

# 3. Wait a moment for services to start
echo ""
echo "3. Waiting for services to initialize..."
sleep 5

# 4. Check status
echo ""
echo "4. Dev container status:"
docker ps --filter "name=bot-dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 5. Check backend logs
echo ""
echo "5. Backend logs (last 20 lines):"
docker logs bot-dev-backend --tail=20 2>&1 | tail -20

# 6. Test health endpoint
echo ""
echo "6. Testing health endpoint:"
curl -s http://localhost:8001/health | head -5 || echo "❌ Health check failed"

echo ""
echo "✅ Dev services started!"
echo ""
echo "Check logs with: docker logs bot-dev-backend --tail=50"
