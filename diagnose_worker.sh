#!/bin/bash
# Diagnose worker container issues

echo "🔍 Diagnosing worker container..."

# Check if container exists
CONTAINER_ID="294defed3191"
echo "📋 Checking container $CONTAINER_ID..."
docker inspect "$CONTAINER_ID" 2>/dev/null && echo "✅ Container exists" || echo "❌ Container not found"

# Check all worker-related containers
echo ""
echo "📋 All containers with 'worker' in name:"
docker ps -a --filter "name=worker" --format "{{.ID}} {{.Names}} {{.Status}}"

# Check container logs directly
echo ""
echo "📋 Logs from container $CONTAINER_ID:"
docker logs "$CONTAINER_ID" --tail=50 2>&1 || echo "Could not get logs"

# Check if worker container is running
echo ""
echo "📋 Worker container status:"
docker-compose -f docker-compose.dev.yml ps worker

# Try to get logs using docker directly
WORKER_CONTAINER=$(docker ps -a --filter "name=bot-dev-worker" --format "{{.ID}}" | head -1)
if [ -n "$WORKER_CONTAINER" ]; then
    echo ""
    echo "📋 Logs from bot-dev-worker ($WORKER_CONTAINER):"
    docker logs "$WORKER_CONTAINER" --tail=100 2>&1
else
    echo ""
    echo "❌ No bot-dev-worker container found"
fi

# Check for any exited containers
echo ""
echo "📋 Exited containers:"
docker ps -a --filter "status=exited" --format "{{.ID}} {{.Names}} {{.Status}}" | grep -i worker || echo "No exited worker containers"
