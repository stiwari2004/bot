#!/bin/bash
# Check backend health and diagnose issues

set -e

echo "🏥 Checking backend health..."
echo ""

# Check which compose file is being used
COMPOSE_FILE="docker-compose.yml"
if docker ps --format "{{.Names}}" | grep -q "bot_backend"; then
    # Check if network exists (indicates production)
    if docker network ls | grep -q "bot_app-network"; then
        COMPOSE_FILE="docker-compose.production.yml"
        echo "📋 Using production compose file"
    else
        echo "📋 Using standard compose file"
    fi
fi

# Check backend container status
echo ""
echo "📦 Backend container status:"
docker ps --filter "name=bot_backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check backend logs
echo ""
echo "📋 Recent backend logs (last 20 lines):"
docker-compose -f $COMPOSE_FILE logs --tail=20 backend

# Check backend health endpoint
echo ""
echo "🏥 Testing backend health endpoint:"
BACKEND_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bot_backend_1 2>/dev/null || echo "localhost")
echo "   Backend IP: $BACKEND_IP"

# Try to curl health endpoint from inside container
echo ""
echo "   Testing from inside container..."
docker exec bot_backend_1 curl -f http://localhost:8000/health 2>/dev/null && echo "✅ Health check passed" || echo "❌ Health check failed"

# Check backend dependencies
echo ""
echo "🔍 Checking backend dependencies:"
echo "   PostgreSQL connection:"
docker exec bot_backend_1 python -c "import psycopg2; psycopg2.connect('postgresql://postgres:password@postgres:5432/troubleshooting_ai')" 2>/dev/null && echo "   ✅ PostgreSQL connection OK" || echo "   ❌ PostgreSQL connection failed"

echo ""
echo "   Redis connection:"
docker exec bot_backend_1 python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" 2>/dev/null && echo "   ✅ Redis connection OK" || echo "   ❌ Redis connection failed"

# Check environment variables
echo ""
echo "🔍 Checking backend environment:"
docker exec bot_backend_1 env | grep -E "DATABASE_URL|REDIS_URL|SECRET_KEY" | sed 's/=.*/=***/' || echo "   Could not check environment"

echo ""
echo "💡 If backend is unhealthy, common fixes:"
echo "   1. Check database connection: docker-compose -f $COMPOSE_FILE logs postgres"
echo "   2. Restart backend: docker-compose -f $COMPOSE_FILE restart backend"
echo "   3. Check backend logs: docker-compose -f $COMPOSE_FILE logs backend"



