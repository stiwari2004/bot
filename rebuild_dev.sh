#!/bin/bash
# Rebuild and start dev environment

set -e

echo "🔨 Rebuilding dev environment..."

# Step 1: Stop and remove dev containers
echo "📦 Stopping dev..."
docker-compose -f docker-compose.dev.yml stop 2>/dev/null || true

# Step 2: Remove dev containers
echo "🗑️  Removing dev containers..."
docker-compose -f docker-compose.dev.yml rm -f 2>/dev/null || true

# Also remove by name patterns
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-frontend bot-dev-worker 2>/dev/null || true

# Step 3: Rebuild
echo "🔨 Building dev images..."
docker-compose -f docker-compose.dev.yml build

# Step 4: Start
echo "🚀 Starting dev services..."
docker-compose -f docker-compose.dev.yml up -d

echo ""
echo "✅ Dev rebuild complete!"
echo ""
echo "📋 Checking status..."
docker-compose -f docker-compose.dev.yml ps
