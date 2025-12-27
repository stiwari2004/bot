#!/bin/bash
# Quick fix: Just restart Docker daemon to clear containerd leases
# Use this if you just want to restart Docker without rebuilding

set -e

echo "🔄 Restarting Docker daemon to fix containerd lease issues..."

# Restart Docker
sudo systemctl restart docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 5

# Verify Docker is running
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is running!"
    echo ""
    echo "Now you can retry your build with:"
    echo "   docker-compose build"
    echo "   docker-compose up -d"
else
    echo "❌ Docker failed to start. Check status with:"
    echo "   sudo systemctl status docker"
    exit 1
fi

