#!/bin/bash
# Fix ContainerConfig error for backend by removing old container and rebuilding

set -e

echo "🔧 Fixing Backend ContainerConfig Error"
echo "========================================"
echo ""

# Step 1: Stop backend container
echo "🛑 Step 1: Stopping backend container..."
docker-compose -f docker-compose.production.yml stop backend 2>/dev/null || true
echo "✅ Backend stopped"
echo ""

# Step 2: Remove backend container (not the image, just the container)
echo "🗑️  Step 2: Removing backend container..."
docker-compose -f docker-compose.production.yml rm -f backend 2>/dev/null || true
# Also try removing by name directly
docker rm -f bot_backend_1 2>/dev/null || true
docker rm -f $(docker ps -aq --filter "name=bot.*backend") 2>/dev/null || true
echo "✅ Backend container removed"
echo ""

# Step 3: Build fresh backend image
echo "🔨 Step 3: Building fresh backend image..."
docker-compose -f docker-compose.production.yml build --no-cache backend
echo "✅ Backend image built"
echo ""

# Step 4: Start backend
echo "🚀 Step 4: Starting backend..."
docker-compose -f docker-compose.production.yml up -d backend
echo "✅ Backend started"
echo ""

# Step 5: Wait and check status
echo "⏳ Step 5: Waiting for backend to be healthy..."
sleep 10

if docker ps | grep -q "bot_backend"; then
    echo "✅ Backend container is running"
    echo ""
    echo "📋 Checking backend logs (last 10 lines)..."
    docker-compose -f docker-compose.production.yml logs --tail=10 backend
else
    echo "❌ Backend container failed to start"
    echo "   Check logs: docker-compose -f docker-compose.production.yml logs backend"
fi

echo ""
echo "✅ Fix complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Check if super-admin endpoints are working:"
echo "      curl -i http://localhost:8000/api/v1/super-admin/overview"
echo "   2. If still 404, check logs for import errors:"
echo "      docker-compose -f docker-compose.production.yml logs backend | grep -i 'super\|error'"
echo ""



