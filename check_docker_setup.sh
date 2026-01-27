#!/bin/bash
# Check Docker Setup - Inspect actual containers and images
# This script helps identify the actual container/image naming

echo "=== Docker Setup Inspection ==="
echo ""

echo "1. All containers (running and stopped):"
echo "----------------------------------------"
docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
echo ""

echo "2. All bot-related containers:"
echo "----------------------------------------"
docker ps -a --filter "name=bot" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
echo ""

echo "3. All bot-related images:"
echo "----------------------------------------"
docker images --filter "reference=*bot*" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"
echo ""

echo "4. Images built from docker-compose:"
echo "----------------------------------------"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | grep -E "(bot|backend|frontend|worker)" || echo "No matching images found"
echo ""

echo "5. Volumes:"
echo "----------------------------------------"
docker volume ls | grep bot || echo "No bot volumes found"
echo ""

echo "6. Networks:"
echo "----------------------------------------"
docker network ls | grep bot || echo "No bot networks found"
echo ""

echo "7. Container details for bot-prod-backend:"
echo "----------------------------------------"
docker inspect bot-prod-backend 2>/dev/null | jq -r '.[0] | {Name: .Name, Image: .Config.Image, ImageID: .Image, State: .State.Status}' 2>/dev/null || echo "Container bot-prod-backend not found"
echo ""

echo "8. Container details for bot-dev-backend:"
echo "----------------------------------------"
docker inspect bot-dev-backend 2>/dev/null | jq -r '.[0] | {Name: .Name, Image: .Config.Image, ImageID: .Image, State: .State.Status}' 2>/dev/null || echo "Container bot-dev-backend not found"
echo ""

echo "9. Docker Compose projects:"
echo "----------------------------------------"
echo "Checking for docker-compose projects..."
docker ps -a --format "{{.Label \"com.docker.compose.project\"}}" | sort -u | grep -v "^$" || echo "No compose projects found"
echo ""

echo "=== Inspection Complete ==="
echo ""
echo "Use this information to determine the correct container/image names."
