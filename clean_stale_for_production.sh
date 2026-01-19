#!/bin/bash
# Clean up stale containers blocking production startup

set -e

echo "🧹 Cleaning up stale containers for production..."

# Stop and remove dev containers that might conflict
echo "📦 Stopping dev containers..."
docker-compose -f docker-compose.dev.yml stop 2>/dev/null || true

# Remove stale containers by name pattern
echo "🗑️  Removing stale containers..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -E "bot-dev-|4f0d5320958a" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Remove specific stale containers mentioned in error
docker rm -f 4f0d5320958a_bot-dev-postgres 2>/dev/null || true
docker rm -f bot-dev-postgres bot-dev-redis bot-dev-backend bot-dev-frontend bot-dev-worker 2>/dev/null || true

# Remove any containers with partial matches
echo "🔍 Removing containers matching patterns..."
docker ps -a --format "{{.ID}} {{.Names}}" | grep -i "bot-dev" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "📋 Now try starting production:"
echo "   docker-compose -f docker-compose.production.yml up -d"
