#!/bin/bash
# Script to update server with latest fixes
# Run this on the server: srv640992

set -e

echo "=== Updating bot application ==="
cd /opt/opsbot/bot

echo "1. Pulling latest code from dev branch..."
git fetch origin
git checkout dev
git pull origin dev

echo "2. Stopping dev containers..."
docker-compose -f docker-compose.dev.yml -p bot-dev down

echo "3. Rebuilding backend (no cache)..."
docker-compose -f docker-compose.dev.yml -p bot-dev build --no-cache backend

echo "4. Starting dev containers..."
docker-compose -f docker-compose.dev.yml -p bot-dev up -d

echo "5. Checking backend logs..."
sleep 5
docker-compose -f docker-compose.dev.yml -p bot-dev logs --tail=50 backend

echo ""
echo "=== Dev update complete ==="
echo ""
echo "For production, run:"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod down"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend"
echo "  docker-compose -f docker-compose.production.yml -p bot-prod up -d"
