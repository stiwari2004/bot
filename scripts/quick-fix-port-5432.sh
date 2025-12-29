#!/bin/bash
# Quick fix for port 5432 conflict (PostgreSQL)
# This stops host PostgreSQL service if running

set -e

echo "🔧 Quick fix for port 5432 conflict..."
echo ""

# Check if PostgreSQL is running on host
if systemctl is-active --quiet postgresql 2>/dev/null || systemctl is-active --quiet postgresql@* 2>/dev/null; then
    echo "⚠️  PostgreSQL service is running on the host (port 5432)"
    echo "   Stopping host PostgreSQL to free port for Docker..."
    sudo systemctl stop postgresql 2>/dev/null || true
    sudo systemctl stop postgresql@* 2>/dev/null || true
    echo "✅ Host PostgreSQL stopped"
else
    echo "✅ No PostgreSQL service running on host"
fi

# Check for Docker containers using port 5432
echo ""
echo "🔍 Checking for Docker containers using port 5432..."
CONFLICTING=$(docker ps --filter "publish=5432" --format "{{.Names}}" 2>/dev/null || true)

if [ ! -z "$CONFLICTING" ]; then
    echo "⚠️  Found Docker containers using port 5432: $CONFLICTING"
    echo "   Stopping conflicting containers..."
    docker stop $CONFLICTING 2>/dev/null || true
    docker rm $CONFLICTING 2>/dev/null || true
    echo "✅ Conflicting containers stopped"
else
    echo "✅ No Docker containers using port 5432"
fi

# Check for any process using port 5432
echo ""
if command -v lsof > /dev/null 2>&1; then
    PID=$(lsof -ti :5432 2>/dev/null || true)
    if [ ! -z "$PID" ]; then
        echo "⚠️  Found process(es) using port 5432: $PID"
        echo "   Process details:"
        ps -p $PID -o pid,cmd 2>/dev/null || true
        echo ""
        read -p "   Kill these processes? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$PID" | xargs -r kill -9 2>/dev/null || true
            echo "✅ Killed processes on port 5432"
        fi
    else
        echo "✅ Port 5432 is now free"
    fi
fi

echo ""
echo "✅ Port 5432 should now be available!"
echo ""
echo "Now try: docker-compose up -d"



