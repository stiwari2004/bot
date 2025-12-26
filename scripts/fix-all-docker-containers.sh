#!/bin/bash
# Comprehensive fix for Docker Compose ContainerConfig errors
# This removes ALL containers and rebuilds from scratch

set -e

echo "🔧 Fixing Docker Compose ContainerConfig errors..."
echo "⚠️  This will remove ALL containers. Database volumes will be preserved."

# Step 1: Stop all containers
echo ""
echo "📦 Step 1: Stopping all containers..."
docker-compose down || true
docker stop $(docker ps -aq) 2>/dev/null || true

# Step 2: Remove ALL containers (including orphaned ones like bot-proxy)
echo ""
echo "🗑️  Step 2: Removing all containers..."
docker ps -aq | xargs -r docker rm -f || true

# Step 3: Remove problematic images
echo ""
echo "🗑️  Step 3: Removing potentially corrupted images..."
docker rmi bot_frontend bot_backend bot_worker 2>/dev/null || true
docker rmi pgvector/pgvector:pg15 redis:7.2-alpine 2>/dev/null || true

# Step 4: Clean up Docker system
echo ""
echo "🧹 Step 4: Pruning Docker system..."
docker system prune -f

# Step 5: Remove dangling images
echo ""
echo "🧹 Step 5: Removing dangling images..."
docker image prune -f

# Step 6: Pull fresh base images
echo ""
echo "📥 Step 6: Pulling fresh base images..."
docker pull pgvector/pgvector:pg15 || true
docker pull redis:7.2-alpine || true
docker pull node:20-bullseye-slim || true

# Step 7: Rebuild and start everything
echo ""
echo "🚀 Step 7: Rebuilding and starting all services..."
docker-compose up -d --build --force-recreate

# Step 8: Show status
echo ""
echo "✅ Done! Checking container status..."
sleep 5
docker-compose ps

echo ""
echo "📊 Container health status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "💡 If containers are unhealthy, check logs with:"
echo "   docker-compose logs [service_name]"

