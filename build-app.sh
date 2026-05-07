#!/usr/bin/env bash
# Build the complete Resolvify app image (backend + frontend + discovery-agent).
# Run from repo root. Use this image for PAAS/production so discovery endpoints work.
set -e
cd "$(dirname "$0")"
docker build -f Dockerfile.combined -t resolvify-app:latest .
echo "Built resolvify-app:latest (backend + frontend + discovery-agent)."
echo "Run: docker run -p 8000:8000 ... resolvify-app:latest"
