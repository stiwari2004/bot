#!/bin/bash
# Fix stale backend container blocking worker startup

set -e

echo "🔧 Fixing stale backend container..."

# Remove the stale backend container by ID
STALE_CONTAINER="6bafe2eb1a7e_bot-dev-backend"
echo "🗑️  Removing stale container: $STALE_CONTAINER"
docker rm -f "$STALE_CONTAINER" 2>/dev/null || true

# Also try removing by name
echo "🗑️  Removing by container name..."
docker rm -f bot-dev-backend 2>/dev/null || true

# Remove any containers with partial match
echo "🔍 Removing any containers matching pattern..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -E "bot-dev-backend|6bafe2eb1a7e" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo "✅ Stale containers removed"
echo ""
echo "📋 Now you can start the worker:"
echo "   docker-compose -f docker-compose.dev.yml up -d worker"
