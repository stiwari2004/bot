#!/bin/bash
# Fix Docker port conflicts (ports already in use)
# This script identifies what's using the ports and helps resolve conflicts

set -e

echo "🔍 Checking for port conflicts..."
echo ""

# Check common ports used by the application
PORTS=(5432 6379 8000 3000)

for PORT in "${PORTS[@]}"; do
    echo "Checking port $PORT..."
    
    # Check if port is in use
    if lsof -i :$PORT > /dev/null 2>&1 || netstat -tuln | grep -q ":$PORT "; then
        echo "⚠️  Port $PORT is in use!"
        
        # Try to find what's using it
        echo "   Finding process using port $PORT..."
        
        # Try lsof first
        if command -v lsof > /dev/null 2>&1; then
            lsof -i :$PORT | head -5
        # Fallback to netstat
        elif command -v netstat > /dev/null 2>&1; then
            netstat -tulnp | grep ":$PORT " | head -5
        # Fallback to ss
        elif command -v ss > /dev/null 2>&1; then
            ss -tulnp | grep ":$PORT " | head -5
        fi
        
        echo ""
    else
        echo "✅ Port $PORT is available"
    fi
done

echo ""
echo "🔧 Fixing port conflicts..."
echo ""

# Check for running PostgreSQL outside Docker
if systemctl is-active --quiet postgresql || systemctl is-active --quiet postgresql@*; then
    echo "⚠️  PostgreSQL service is running on the host!"
    echo "   Options:"
    echo "   1. Stop PostgreSQL service: sudo systemctl stop postgresql"
    echo "   2. Change Docker port mapping in docker-compose.yml"
    echo ""
    read -p "   Stop PostgreSQL service? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl stop postgresql || true
        sudo systemctl stop postgresql@* || true
        echo "✅ PostgreSQL service stopped"
    fi
fi

# Check for running Redis outside Docker
if systemctl is-active --quiet redis || systemctl is-active --quiet redis-server; then
    echo "⚠️  Redis service is running on the host!"
    echo ""
    read -p "   Stop Redis service? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl stop redis || true
        sudo systemctl stop redis-server || true
        echo "✅ Redis service stopped"
    fi
fi

# Check for Docker containers using the ports
echo ""
echo "🔍 Checking for Docker containers using ports..."
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(5432|6379|8000|3000)" || echo "No Docker containers found using these ports"

# Stop any conflicting Docker containers
echo ""
echo "🛑 Stopping any conflicting containers..."
docker-compose down || true

# Kill any processes still using the ports (be careful!)
for PORT in "${PORTS[@]}"; do
    if lsof -ti :$PORT > /dev/null 2>&1; then
        PIDS=$(lsof -ti :$PORT)
        if [ ! -z "$PIDS" ]; then
            echo "⚠️  Found processes using port $PORT: $PIDS"
            read -p "   Kill these processes? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "$PIDS" | xargs -r kill -9
                echo "✅ Killed processes on port $PORT"
            fi
        fi
    fi
done

echo ""
echo "✅ Port conflict check complete!"
echo ""
echo "Now try starting Docker Compose again:"
echo "   docker-compose up -d"

