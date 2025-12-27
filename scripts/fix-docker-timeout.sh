#!/bin/bash
# Fix Docker Compose timeout issues
# Increases timeout and optimizes Docker for slow operations

set -e

echo "🔧 Fixing Docker Compose timeout issues..."
echo ""

# Step 1: Set environment variable for higher timeout
echo "⏱️  Step 1: Setting higher Docker Compose timeout..."
export COMPOSE_HTTP_TIMEOUT=300  # 5 minutes
export DOCKER_CLIENT_TIMEOUT=300
export COMPOSE_HTTP_TIMEOUT=300

# Make it permanent in current shell session
echo "export COMPOSE_HTTP_TIMEOUT=300" >> ~/.bashrc
echo "export DOCKER_CLIENT_TIMEOUT=300" >> ~/.bashrc

echo "✅ Timeout set to 300 seconds (5 minutes)"

# Step 2: Check Docker daemon health
echo ""
echo "🏥 Step 2: Checking Docker daemon health..."
if docker info > /dev/null 2>&1; then
    echo "✅ Docker daemon is running"
else
    echo "❌ Docker daemon is not responding"
    echo "   Restarting Docker..."
    sudo systemctl restart docker
    sleep 5
fi

# Step 3: Check disk space
echo ""
echo "💾 Step 3: Checking disk space..."
df -h / | tail -1
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️  Disk usage is high: ${DISK_USAGE}%"
    echo "   Consider cleaning up Docker: docker system prune -a"
else
    echo "✅ Disk space is OK: ${DISK_USAGE}% used"
fi

# Step 4: Check Docker system resources
echo ""
echo "📊 Step 4: Checking Docker system resources..."
docker system df

# Step 5: Clean up if needed
echo ""
read -p "🧹 Clean up Docker system (remove unused images/containers)? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning up Docker system..."
    docker system prune -f --volumes=false
    echo "✅ Cleanup complete"
fi

# Step 6: Start services with increased timeout
echo ""
echo "🚀 Step 6: Starting services with increased timeout..."
echo "   Using COMPOSE_HTTP_TIMEOUT=300"
COMPOSE_HTTP_TIMEOUT=300 docker-compose up -d

echo ""
echo "✅ Done! Services should be starting..."
echo ""
echo "💡 If timeouts persist, try:"
echo "   1. Restart Docker: sudo systemctl restart docker"
echo "   2. Increase timeout further: export COMPOSE_HTTP_TIMEOUT=600"
echo "   3. Start services one by one: docker-compose up -d postgres redis"
echo "   4. Check logs: docker-compose logs [service_name]"

