#!/bin/bash
# Complete cleanup and switch to production compose
# Removes ALL containers and images, then recreates with production config

set -e

echo "🧹 Complete cleanup and switch to production Docker Compose..."
echo "⚠️  This will remove ALL containers and images (volumes preserved)"
echo ""

# Step 1: Stop everything
echo "🛑 Step 1: Stopping all services..."
docker-compose down || true
docker-compose -f docker-compose.production.yml down || true
docker stop $(docker ps -aq) 2>/dev/null || true

# Step 2: Remove ALL containers
echo ""
echo "🗑️  Step 2: Removing all containers..."
docker ps -aq | xargs -r docker rm -f || true

# Step 3: Remove problematic images (but keep base images)
echo ""
echo "🗑️  Step 3: Removing application images..."
docker rmi bot_frontend bot_backend bot_worker 2>/dev/null || true

# Step 4: Clean up Docker (preserving volumes)
echo ""
echo "🧹 Step 4: Cleaning Docker system (volumes preserved)..."
docker system prune -f --volumes=false

# Step 5: Create network if needed
echo ""
echo "🌐 Step 5: Creating Docker network..."
if ! docker network ls | grep -q "bot_app-network"; then
    docker network create bot_app-network
    echo "✅ Network created"
else
    echo "✅ Network already exists"
fi

# Step 6: Set timeout
echo ""
echo "⏱️  Step 6: Setting higher timeout..."
export COMPOSE_HTTP_TIMEOUT=300
export DOCKER_CLIENT_TIMEOUT=300

# Step 7: Start production services
echo ""
echo "🚀 Step 7: Starting production services..."
echo "   Using: docker-compose.production.yml"

# Start postgres
echo "   📦 Starting PostgreSQL..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d postgres
echo "   ⏳ Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
    if docker-compose -f docker-compose.production.yml ps postgres | grep -q "healthy"; then
        echo "   ✅ PostgreSQL is healthy"
        break
    fi
    sleep 2
done

# Start redis
echo ""
echo "   📦 Starting Redis..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d redis
echo "   ⏳ Waiting for Redis to be healthy..."
for i in {1..20}; do
    if docker-compose -f docker-compose.production.yml ps redis | grep -q "healthy\|Up"; then
        echo "   ✅ Redis is running"
        break
    fi
    sleep 2
done

# Start backend
echo ""
echo "   📦 Starting Backend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d backend
echo "   ⏳ Waiting for Backend to become healthy..."
sleep 20

# Check backend health
for i in {1..30}; do
    BACKEND_STATUS=$(docker-compose -f docker-compose.production.yml ps backend | grep -o "healthy\|unhealthy\|Up" | head -1)
    if [ "$BACKEND_STATUS" = "healthy" ]; then
        echo "   ✅ Backend is healthy"
        break
    elif [ "$i" -eq 30 ]; then
        echo "   ⚠️  Backend is not healthy yet, but continuing..."
        echo "   Check logs: docker-compose -f docker-compose.production.yml logs backend"
    fi
    sleep 2
done

# Start frontend
echo ""
echo "   📦 Starting Frontend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d frontend
sleep 10

# Start worker (only if backend is healthy)
echo ""
echo "   📦 Checking Backend health before starting Worker..."
BACKEND_HEALTHY="no"
for i in {1..30}; do
    if docker-compose -f docker-compose.production.yml ps backend 2>/dev/null | grep -q "healthy"; then
        BACKEND_HEALTHY="yes"
        break
    fi
    sleep 2
done

if [ "$BACKEND_HEALTHY" = "yes" ]; then
    echo "   ✅ Backend is healthy, starting Worker..."
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d worker
    sleep 10
    echo "   ✅ Worker started"
else
    echo "   ⚠️  Backend is not healthy yet"
    echo "   Worker will start automatically when backend becomes healthy"
    echo "   Or start manually: docker-compose -f docker-compose.production.yml up -d worker"
fi

# Start proxy if it exists
if grep -q "proxy:" docker-compose.production.yml; then
    echo ""
    echo "   📦 Starting Proxy..."
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.production.yml up -d proxy || {
        echo "   ⚠️  Proxy failed to start (check proxy/conf.d directory)"
    }
fi

# Final status
echo ""
echo "✅ Services started!"
echo ""
echo "📊 Service status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "💡 If any service is unhealthy:"
echo "   Check logs: docker-compose -f docker-compose.production.yml logs [service_name]"
echo "   Restart: docker-compose -f docker-compose.production.yml restart [service_name]"

