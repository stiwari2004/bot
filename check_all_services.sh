#!/bin/bash
# Check all services (dev and prod)

echo "=== All Bot Containers ==="
docker ps -a --filter "name=bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Dev Backend Status ==="
docker ps -a --filter "name=bot-dev-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Production Backend Status ==="
docker ps -a --filter "name=bot-prod_backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Port 8000 (Production) ==="
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep "8000"

echo ""
echo "=== Port 8001 (Dev) ==="
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep "8001"
