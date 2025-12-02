#!/bin/bash
# Reset sandbox environment

echo "🔄 Resetting sandbox environment..."

# Reset database
docker-compose -f docker-compose.sandbox.yml exec -T backend python scripts/reset_sandbox.py

# Reseed data
docker-compose -f docker-compose.sandbox.yml exec -T backend python scripts/seed_sandbox_data.py

echo "✅ Sandbox environment reset and reseeded"



