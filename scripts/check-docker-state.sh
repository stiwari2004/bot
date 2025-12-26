#!/bin/bash
# Check Docker state to diagnose ContainerConfig issues

echo "🔍 Docker State Diagnostic"
echo "=========================="
echo ""

echo "📦 All Containers:"
docker ps -a
echo ""

echo "🖼️  All Images:"
docker images
echo ""

echo "💾 Volumes:"
docker volume ls
echo ""

echo "🌐 Networks:"
docker network ls
echo ""

echo "🔍 Looking for 'bot-proxy' container:"
docker ps -a | grep -i proxy || echo "No proxy container found"
echo ""

echo "🔍 Looking for containers with 'bot' prefix:"
docker ps -a --filter "name=bot" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

echo "📊 Docker system info:"
docker system df
echo ""

echo "⚠️  If you see corrupted containers, run: ./scripts/fix-all-docker-containers.sh"

