#!/bin/bash
# Fix container naming conflict between production and dev

set -e

echo "🔧 Fixing production/dev container conflicts..."

# Check what's running
echo "📋 Current production containers:"
docker-compose -f docker-compose.production.yml ps 2>/dev/null || echo "Production not running"

echo ""
echo "📋 Containers with conflicting names:"
docker ps -a --format "{{.Names}}" | grep -E "^bot_(postgres|redis|backend|frontend|worker)_[0-9]+$" || echo "No conflicting containers found"

echo ""
echo "🗑️  Removing production containers that conflict with dev..."
# Stop production first
docker-compose -f docker-compose.production.yml stop 2>/dev/null || true

# Remove production containers (they don't have explicit names, so they use default naming)
docker ps -a --format "{{.ID}} {{.Names}}" | grep -E "^bot_(postgres|redis|backend|frontend|worker)_[0-9]+$" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

echo ""
echo "✅ Production containers removed"
echo ""
echo "📋 To restart production with proper container names, we need to add container_name to production compose"
echo "   OR use a different project name: docker-compose -f docker-compose.production.yml -p bot-prod up -d"
