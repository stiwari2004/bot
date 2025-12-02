#!/bin/bash
# Start sandbox environment

echo "🚀 Starting sandbox environment..."

docker-compose -f docker-compose.sandbox.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

echo "🌱 Seeding sandbox with sample data..."
docker-compose -f docker-compose.sandbox.yml exec -T backend python scripts/seed_sandbox_data.py

echo ""
echo "✅ Sandbox environment is ready!"
echo ""
echo "🌐 Access points:"
echo "   - Frontend: http://localhost:3001"
echo "   - Backend:  http://localhost:8001"
echo "   - Database: localhost:5433"
echo "   - Redis:    localhost:6380"
echo ""
echo "📋 Demo credentials:"
echo "   - Email: demo@example.com"
echo "   - Password: demo123"



