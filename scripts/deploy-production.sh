#!/bin/bash
# Deploy to production (demo.yourdomain.com)
# Usage: ./scripts/deploy-production.sh

set -e

APP_DIR="/opt/troubleshooting-ai-demo"
COMPOSE_FILE="docker-compose.production.yml"

echo "🚀 Starting production deployment..."
echo "📍 Directory: $APP_DIR"

# Check if directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Error: Application directory not found: $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Pull latest code
echo "📥 Pulling latest code from git..."
git fetch origin
git checkout main
git pull origin main

# Build images
echo "🔨 Building Docker images..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# Stop old containers
echo "🛑 Stopping old containers..."
docker compose -f "$COMPOSE_FILE" down

# Start new containers
echo "▶️  Starting new containers..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up (healthy)"; then
    echo "⚠️  Warning: Some services may not be healthy. Check logs:"
    echo "   docker compose -f $COMPOSE_FILE logs"
fi

# Run database migrations if needed
echo "🔄 Running database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T backend python -m alembic upgrade head 2>/dev/null || echo "No migrations to run"

# Verify deployment
echo "✅ Verifying deployment..."
sleep 5

# Check if services are responding
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is responding"
else
    echo "❌ Backend health check failed"
    exit 1
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is responding"
else
    echo "❌ Frontend is not responding"
    exit 1
fi

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Demo instance: https://demo.yourdomain.com"
echo "🔍 Check logs: docker compose -f $COMPOSE_FILE logs -f"

