#!/bin/bash
# Remove only the conflicting containers - NO network or volume cleanup

echo "Removing conflicting containers..."

# Remove the specific containers mentioned in the error
docker rm -f 012d81c008db8f80e4403ed1d26e4fb4dae0604265ba287445d691a8b74570cc 2>/dev/null || true
docker rm -f 451df6f262bd12b91255dca7d76294b019224841d57c57458e9fb5185e8bc07c 2>/dev/null || true

# Also remove by name in case they still exist
docker rm -f bot-dev-postgres bot-dev-redis 2>/dev/null || true

echo "Done. Now try: docker-compose -f docker-compose.dev.yml up -d --force-recreate"
