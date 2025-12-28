#!/bin/bash
# Fix Docker Compose structural issues
# Handles network creation, proxy service, and timeout issues

set -e

echo "🔧 Fixing Docker Compose structural issues..."
echo ""

# Step 1: Check which compose file is being used
COMPOSE_FILE="docker-compose.yml"
if [ -f "docker-compose.production.yml" ] && [ -f ".env.production" ]; then
    echo "📋 Production compose file detected"
    COMPOSE_FILE="docker-compose.production.yml"
    
    # Check if external network exists
    echo ""
    echo "🌐 Step 1: Checking Docker network..."
    if ! docker network ls | grep -q "bot_app-network"; then
        echo "⚠️  External network 'bot_app-network' does not exist"
        echo "   Creating network..."
        docker network create bot_app-network || true
        echo "✅ Network created"
    else
        echo "✅ Network 'bot_app-network' exists"
    fi
else
    echo "📋 Using standard docker-compose.yml"
fi

# Step 2: Set higher timeout
echo ""
echo "⏱️  Step 2: Setting higher timeout..."
export COMPOSE_HTTP_TIMEOUT=300
export DOCKER_CLIENT_TIMEOUT=300

# Step 3: Stop all services first
echo ""
echo "🛑 Step 3: Stopping all services..."
docker-compose -f $COMPOSE_FILE down || true

# Step 4: Remove problematic containers
echo ""
echo "🗑️  Step 4: Removing problematic containers..."
docker ps -a --filter "name=bot" -q | xargs -r docker rm -f || true

# Step 5: Check for proxy service issues
if grep -q "proxy:" $COMPOSE_FILE 2>/dev/null; then
    echo ""
    echo "🔍 Step 5: Checking proxy configuration..."
    
    # Check if proxy directory exists
    if [ ! -d "proxy/conf.d" ]; then
        echo "⚠️  Proxy directory 'proxy/conf.d' not found"
        echo "   Creating directory structure..."
        mkdir -p proxy/conf.d
        echo "✅ Proxy directory created"
    else
        echo "✅ Proxy directory exists"
    fi
    
    # Check if proxy config files exist
    if [ ! -f "proxy/conf.d/default.conf" ] && [ ! -f "proxy/conf.d/nginx.conf" ]; then
        echo "⚠️  No proxy config files found"
        echo "   You may need to create nginx configuration"
    fi
fi

# Step 6: Start services with proper timeout
echo ""
echo "🚀 Step 6: Starting services with increased timeout..."
echo "   Using COMPOSE_HTTP_TIMEOUT=300"

# Start services one by one to avoid timeouts
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d postgres
sleep 10

COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d redis
sleep 5

COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d backend
sleep 10

# Try frontend with verbose output
echo ""
echo "📦 Starting frontend (this may take a while)..."
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d frontend || {
    echo "⚠️  Frontend failed to start, trying with verbose output..."
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d --verbose frontend
}

# If proxy exists, start it last
if grep -q "proxy:" $COMPOSE_FILE 2>/dev/null; then
    echo ""
    echo "📦 Starting proxy..."
    COMPOSE_HTTP_TIMEOUT=300 docker-compose -f $COMPOSE_FILE up -d proxy || {
        echo "⚠️  Proxy failed to start (this is OK if nginx config is missing)"
    }
fi

# Check status
echo ""
echo "✅ Services started! Checking status..."
sleep 5
docker-compose -f $COMPOSE_FILE ps

echo ""
echo "💡 If services are unhealthy, check logs:"
echo "   docker-compose -f $COMPOSE_FILE logs [service_name]"

