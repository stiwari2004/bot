#!/bin/bash
# Clean rebuild of dev backend (fixes "image already exists" and ensures worker events route)
# Run from repo root: ./scripts/dev-rebuild-backend.sh

set -e
PROJECT="bot-dev"
COMPOSE="docker-compose.dev.yml"
BACKEND_IMAGE="bot-dev_backend"

echo "=== Dev Backend Clean Rebuild ==="
echo ""

echo "1. Removing existing backend image (if present)..."
docker image rm "${BACKEND_IMAGE}:latest" 2>/dev/null || true
echo "   Done."
echo ""

echo "2. Building backend (--no-cache)..."
docker compose -f "$COMPOSE" -p "$PROJECT" build --no-cache backend
echo "   Done."
echo ""

echo "3. Restarting backend service..."
docker compose -f "$COMPOSE" -p "$PROJECT" up -d backend
echo "   Done."
echo ""
echo "=== Done ==="
echo "Worker events route: POST /api/v1/agent/workers/events"
