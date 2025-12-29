#!/bin/bash
# Start Docker services one by one to avoid timeouts
# Useful when Docker is slow or system is under load

set -e

echo "🐢 Starting services slowly (one by one)..."
echo ""

# Set higher timeout
export COMPOSE_HTTP_TIMEOUT=300

# Step 1: Start postgres first
echo "📦 Step 1: Starting PostgreSQL..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d postgres
echo "⏳ Waiting for PostgreSQL to be healthy..."
sleep 10

# Step 2: Start redis
echo ""
echo "📦 Step 2: Starting Redis..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d redis
echo "⏳ Waiting for Redis to start..."
sleep 5

# Step 3: Start backend
echo ""
echo "📦 Step 3: Starting Backend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d backend
echo "⏳ Waiting for Backend to start..."
sleep 10

# Step 4: Start frontend
echo ""
echo "📦 Step 4: Starting Frontend..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d frontend
echo "⏳ Waiting for Frontend to start..."
sleep 5

# Step 5: Start worker (optional)
echo ""
read -p "📦 Start worker? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d worker
fi

# Check status
echo ""
echo "✅ All services started!"
echo ""
echo "📊 Service status:"
docker-compose ps

echo ""
echo "💡 Check logs if services are unhealthy:"
echo "   docker-compose logs [service_name]"



