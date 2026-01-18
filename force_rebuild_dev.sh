#!/bin/bash
# Force complete rebuild of dev environment - no cache, fresh images

set -e

COMPOSE_FILE="docker-compose.dev.yml"

echo "🔥 Force rebuilding dev environment (no cache)..."
echo ""

# Step 1: Stop everything
echo "📦 Stopping services..."
docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# Step 2: Remove containers
echo "🗑️  Removing containers..."
docker-compose -f "$COMPOSE_FILE" rm -f 2>/dev/null || true

# Step 3: Remove images (force)
echo "🗑️  Removing images..."
docker-compose -f "$COMPOSE_FILE" down --rmi all 2>/dev/null || true

# Step 4: Build without cache
echo "🔨 Building services without cache (this will take time)..."
docker-compose -f "$COMPOSE_FILE" build --no-cache

# Step 5: Start fresh
echo "🚀 Starting services..."
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "✅ Force rebuild complete!"
echo ""
echo "📋 Checking container status..."
docker-compose -f "$COMPOSE_FILE" ps
