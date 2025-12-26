#!/bin/bash
# Comprehensive fix for Docker Compose ContainerConfig errors
# This removes ALL containers and rebuilds from scratch
# 
# ⚠️  IMPORTANT: This script PRESERVES all database volumes and data.
#     Only containers and images are removed. Volumes are NEVER deleted.

set -e

echo "🔧 Fixing Docker Compose ContainerConfig errors..."
echo "⚠️  This will remove ALL containers and images."
echo "✅ Database volumes and data will be PRESERVED (NOT deleted)."

# Step 1: Stop all containers
echo ""
echo "📦 Step 1: Stopping all containers..."
docker-compose down || true
docker stop $(docker ps -aq) 2>/dev/null || true

# Step 2: Remove ALL containers (including orphaned ones like bot-proxy)
# NOTE: This does NOT delete volumes - data is safe
echo ""
echo "🗑️  Step 2: Removing all containers (volumes preserved)..."
docker ps -aq | xargs -r docker rm -f || true

# Step 3: Remove problematic images
# NOTE: This does NOT delete volumes - data is safe
echo ""
echo "🗑️  Step 3: Removing potentially corrupted images (volumes preserved)..."
docker rmi bot_frontend bot_backend bot_worker 2>/dev/null || true
docker rmi pgvector/pgvector:pg15 redis:7.2-alpine 2>/dev/null || true

# Step 4: Clean up Docker system (EXCLUDING volumes)
# CRITICAL: --volumes=false ensures NO volumes are deleted
echo ""
echo "🧹 Step 4: Pruning Docker system (volumes EXCLUDED - data safe)..."
docker system prune -f --volumes=false

# Step 5: Remove dangling images only (NOT volumes)
echo ""
echo "🧹 Step 5: Removing dangling images (volumes preserved)..."
docker image prune -f

# Step 6: Pull fresh base images
echo ""
echo "📥 Step 6: Pulling fresh base images..."
docker pull pgvector/pgvector:pg15 || true
docker pull redis:7.2-alpine || true
docker pull node:20-bullseye-slim || true

# Step 7: Rebuild and start everything
# NOTE: Existing volumes will be reattached automatically - data preserved
echo ""
echo "🚀 Step 7: Rebuilding and starting all services..."
echo "   (Existing database volumes will be reattached - all data preserved)"
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
echo ""
echo "✅ All database volumes and data have been preserved."
echo "   Your PostgreSQL and Redis data is safe and will be reattached."

