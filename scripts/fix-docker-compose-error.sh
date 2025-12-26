#!/bin/bash
# Fix Docker Compose 'ContainerConfig' KeyError
# This error occurs when container metadata is corrupted

set -e

echo "🔧 Fixing Docker Compose ContainerConfig error..."

# Step 1: Stop all containers
echo "📦 Stopping all containers..."
docker-compose down || true

# Step 2: Remove problematic containers
echo "🗑️  Removing old containers..."
docker ps -a --filter "name=bot-postgres" --filter "name=bot-redis" -q | xargs -r docker rm -f || true

# Step 3: Remove the problematic images (postgres and redis)
echo "🗑️  Removing postgres and redis images..."
docker rmi pgvector/pgvector:pg15 redis:7.2-alpine || true

# Step 4: Prune Docker system to clean up
echo "🧹 Pruning Docker system..."
docker system prune -f

# Step 5: Remove volumes (optional - only if you want fresh databases)
# Uncomment the next line if you want to start with fresh databases
# docker volume rm bot_postgres_data bot_redis_data || true

# Step 6: Pull fresh images
echo "📥 Pulling fresh images..."
docker pull pgvector/pgvector:pg15
docker pull redis:7.2-alpine

# Step 7: Rebuild and start
echo "🚀 Rebuilding and starting services..."
docker-compose up -d --build

echo "✅ Done! Check status with: docker-compose ps"

