#!/bin/bash
# Fix worker container unhealthy issue

set -e

echo "=== Diagnosing Worker Health Issue ==="
echo ""

# Check which container is unhealthy
echo "1. Checking container status..."
docker ps -a --filter "id=5af5db31db90" --format "{{.Names}}\t{{.Status}}" || echo "Container ID not found, checking by name..."

# Check backend status
echo ""
echo "2. Backend container status:"
docker ps -a --filter "name=bot-dev-backend" --format "{{.Names}}\t{{.Status}}"

# Check backend logs
echo ""
echo "3. Backend logs (last 30 lines):"
docker logs bot-dev-backend --tail 30 2>&1 || echo "Could not get backend logs"

# Check if backend health endpoint works
echo ""
echo "4. Testing backend health endpoint:"
docker exec bot-dev-backend curl -f http://localhost:8000/health 2>&1 || echo "Health check failed - backend may not be ready yet"

# Check worker logs if it exists
echo ""
echo "5. Worker container status:"
docker ps -a --filter "name=bot-dev-worker" --format "{{.Names}}\t{{.Status}}"

echo ""
echo "=== Diagnosis Complete ==="
echo ""
echo "If backend is not healthy, try:"
echo "1. Wait 30 seconds and check again: docker logs bot-dev-backend --tail 20"
echo "2. Or change worker dependency to 'service_started' instead of 'service_healthy'"
echo "3. Or restart backend: docker-compose -f docker-compose.dev.yml -p bot-dev restart backend"
