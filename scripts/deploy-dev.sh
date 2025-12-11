#!/bin/bash
# Deploy to development instance (dev.yourdomain.com)
# Usage: ./scripts/deploy-dev.sh

set -e

APP_DIR="/opt/troubleshooting-ai-dev"
COMPOSE_FILE="docker-compose.dev.yml"

echo "🚀 Starting development deployment..."
echo "📍 Directory: $APP_DIR"

# Check if directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Error: Application directory not found: $APP_DIR"
    echo "   Create it with: sudo mkdir -p $APP_DIR && sudo chown \$USER:\$USER $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Pull latest code
echo "📥 Pulling latest code from git..."
git fetch origin
git checkout dev  # or main, depending on your branch strategy
git pull origin dev

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
if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo "⚠️  Warning: Some services may not be healthy. Check logs:"
    echo "   docker compose -f $COMPOSE_FILE logs"
fi

# Verify deployment
echo "✅ Verifying deployment..."
sleep 5

# Check if services are responding (using dev ports)
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Backend is responding"
else
    echo "❌ Backend health check failed"
    exit 1
fi

if curl -f http://localhost:3001 > /dev/null 2>&1; then
    echo "✅ Frontend is responding"
else
    echo "❌ Frontend is not responding"
    exit 1
fi

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Dev instance: https://dev.yourdomain.com"
echo "🔍 Check logs: docker compose -f $COMPOSE_FILE logs -f"

