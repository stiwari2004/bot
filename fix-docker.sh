#!/bin/bash
# Script to completely clean up and restart Docker containers
# Run this on your server to fix the ContainerConfig errors

set -e

cd /opt/opsbot/bot

echo "=== Stopping all containers ==="
docker-compose -f docker-compose.dev.yml down --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.production.yml down --remove-orphans 2>/dev/null || true

echo "=== Removing all bot containers ==="
# Remove by name patterns
docker ps -a --filter "name=bot" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=bot-dev" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Remove specific problematic containers
docker rm -f bot_redis_1 bot_postgres_1 bot_redis bot_postgres 2>/dev/null || true
docker rm -f bot-dev-redis bot-dev-postgres bot-dev-backend bot-dev-frontend bot-dev-worker 2>/dev/null || true

echo "=== Cleaning up networks ==="
# Remove and recreate dev network
docker network rm bot_app-dev-network 2>/dev/null || true
docker network create bot_app-dev-network 2>/dev/null || true

# Create production network if it doesn't exist
docker network create bot_app-network 2>/dev/null || true

echo "=== Starting dev environment ==="
# Start postgres and redis first
docker-compose -f docker-compose.dev.yml up -d postgres redis

echo "=== Waiting for postgres and redis to be healthy ==="
sleep 15

# Check if they're running
if ! docker ps | grep -q bot-dev-postgres; then
    echo "ERROR: Postgres failed to start"
    exit 1
fi

if ! docker ps | grep -q bot-dev-redis; then
    echo "ERROR: Redis failed to start"
    exit 1
fi

echo "=== Starting backend and other services ==="
docker-compose -f docker-compose.dev.yml up -d

echo "=== Checking status ==="
docker-compose -f docker-compose.dev.yml ps

echo "=== Testing backend health ==="
sleep 5
docker exec bot-dev-backend curl -f http://localhost:8000/health || echo "Backend health check failed"

echo "=== Done ==="

