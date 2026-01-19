#!/bin/bash
# Remove stale containers blocking worker startup

set -e

echo "🔧 Removing stale containers blocking worker..."

# Remove the stale backend container
STALE_CONTAINER="8d56ce5bb796_bot-dev-backend"
echo "🗑️  Removing stale container: $STALE_CONTAINER"
docker rm -f "$STALE_CONTAINER" 2>/dev/null || true

# Also remove by name
echo "🗑️  Removing by container name..."
docker rm -f bot-dev-backend 2>/dev/null || true

# Remove any containers with partial match
echo "🔍 Removing any containers matching pattern..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -E "bot-dev-backend|8d56ce5bb796" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Check current backend status
echo ""
echo "📋 Current backend status:"
docker-compose -f docker-compose.dev.yml ps backend 2>/dev/null || echo "Backend not running"

echo ""
echo "✅ Stale containers removed"
echo ""
echo "📋 Now you can start the worker:"
echo "   docker-compose -f docker-compose.dev.yml up -d worker"
