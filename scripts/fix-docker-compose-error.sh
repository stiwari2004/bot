#!/bin/bash
# Fix Docker Compose 'ContainerConfig' KeyError
# This error occurs when container metadata is corrupted
#
# ⚠️  IMPORTANT: This script PRESERVES all database volumes and data.
#     Only containers and images are removed. Volumes are NEVER deleted.

set -e

echo "🔧 Fixing Docker Compose ContainerConfig error..."
echo "✅ Database volumes and data will be PRESERVED (NOT deleted)."

# Step 1: Stop all containers
echo "📦 Stopping all containers..."
docker-compose down || true

# Step 2: Remove problematic containers
# NOTE: This does NOT delete volumes - data is safe
echo "🗑️  Removing old containers (volumes preserved)..."
docker ps -a --filter "name=bot-postgres" --filter "name=bot-redis" -q | xargs -r docker rm -f || true

# Step 3: Remove the problematic images (postgres and redis)
# NOTE: This does NOT delete volumes - data is safe
echo "🗑️  Removing postgres and redis images (volumes preserved)..."
docker rmi pgvector/pgvector:pg15 redis:7.2-alpine || true

# Step 4: Prune Docker system to clean up (EXCLUDING volumes)
# CRITICAL: --volumes=false ensures NO volumes are deleted
echo "🧹 Pruning Docker system (volumes EXCLUDED - data safe)..."
docker system prune -f --volumes=false

# Step 5: Volume deletion is COMMENTED OUT - data is preserved
# ⚠️  DO NOT UNCOMMENT - This would delete your database data!
# docker volume rm bot_postgres_data bot_redis_data || true

# Step 6: Pull fresh images
echo "📥 Pulling fresh images..."
docker pull pgvector/pgvector:pg15
docker pull redis:7.2-alpine

# Step 7: Rebuild and start
# NOTE: Existing volumes will be reattached automatically - data preserved
echo "🚀 Rebuilding and starting services..."
echo "   (Existing database volumes will be reattached - all data preserved)"
docker-compose up -d --build

echo "✅ Done! Check status with: docker-compose ps"
echo "✅ All database volumes and data have been preserved."

