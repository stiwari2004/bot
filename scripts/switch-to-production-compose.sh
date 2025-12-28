#!/bin/bash
# Switch from docker-compose.yml to docker-compose.production.yml
# Handles network creation, stops old services, starts production services

set -e

echo "🔄 Switching to production Docker Compose configuration..."
echo ""

# Step 1: Check if production compose file exists
if [ ! -f "docker-compose.production.yml" ]; then
    echo "❌ docker-compose.production.yml not found!"
    exit 1
fi

echo "✅ Production compose file found"

# Step 2: Create required network
echo ""
echo "🌐 Step 1: Creating Docker network..."
if ! docker network ls | grep -q "bot_app-network"; then
    echo "   Creating network 'bot_app-network'..."
    docker network create bot_app-network
    echo "✅ Network created"
else
    echo "✅ Network 'bot_app-network' already exists"
fi

# Step 3: Stop services using standard compose
echo ""
echo "🛑 Step 2: Stopping services from docker-compose.yml..."
docker-compose down || true

# Step 4: Remove old containers
echo ""
echo "🗑️  Step 3: Removing old containers..."
docker ps -a --filter "name=bot" -q | xargs -r docker rm -f || true

# Step 5: Set timeout
echo ""
echo "⏱️  Step 4: Setting higher timeout..."
export COMPOSE_HTTP_TIMEOUT=300
export DOCKER_CLIENT_TIMEOUT=300

# Step 6: Start production services one by one
echo ""
echo "🚀 Step 5: Starting production services..."
echo "   Using: docker-compose.production.yml"

# Start postgres
echo "   📦 Starting PostgreSQL..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d postgres
echo "   ⏳ Waiting for PostgreSQL to be healthy..."
sleep 15

# Start redis
echo "   📦 Starting Redis..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d redis
echo "   ⏳ Waiting for Redis to be healthy..."
sleep 10

# Start backend
echo "   📦 Starting Backend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d backend
echo "   ⏳ Waiting for Backend to start..."
sleep 15

# Start frontend
echo "   📦 Starting Frontend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d frontend
echo "   ⏳ Waiting for Frontend to start..."
sleep 10

# Start worker (optional)
echo ""
read -p "   📦 Start worker? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d worker
fi

# Start proxy if it exists in production compose
if grep -q "proxy:" docker-compose.production.yml; then
    echo ""
    echo "   📦 Starting Proxy..."
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d proxy || {
        echo "   ⚠️  Proxy failed to start (check proxy/conf.d directory)"
    }
fi

# Step 7: Check status
echo ""
echo "✅ Production services started!"
echo ""
echo "📊 Service status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "💡 Useful commands:"
echo "   View logs: docker-compose -f docker-compose.production.yml logs [service_name]"
echo "   Stop all: docker-compose -f docker-compose.production.yml down"
echo "   Restart: docker-compose -f docker-compose.production.yml restart [service_name]"
echo ""
echo "⚠️  Remember: Always use -f docker-compose.production.yml for production!"

