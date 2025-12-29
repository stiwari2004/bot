#!/bin/bash
# Fix Docker build "lease does not exist" error
# This error occurs when containerd has stale leases or Docker daemon needs restart

set -e

echo "🔧 Fixing Docker build lease error..."
echo ""

# Step 1: Stop all containers
echo "📦 Step 1: Stopping all containers..."
docker-compose down || true

# Step 2: Restart Docker daemon (this clears containerd leases)
echo "🔄 Step 2: Restarting Docker daemon..."
echo "   (This will clear containerd leases and fix the build issue)"
sudo systemctl restart docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 5

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please check Docker status manually."
    exit 1
fi

echo "✅ Docker is ready!"

# Step 3: Clean up build cache (optional but recommended)
echo ""
echo "🧹 Step 3: Cleaning Docker build cache..."
docker builder prune -f

# Step 4: Retry the build
echo ""
echo "🚀 Step 4: Rebuilding services..."
docker-compose build --no-cache

# Step 5: Start services
echo ""
echo "🚀 Step 5: Starting services..."
docker-compose up -d

echo ""
echo "✅ Done! Checking container status..."
sleep 5
docker-compose ps

echo ""
echo "💡 If build still fails, try:"
echo "   1. Check disk space: df -h"
echo "   2. Check Docker logs: journalctl -u docker -n 50"
echo "   3. Increase Docker timeout if needed"



