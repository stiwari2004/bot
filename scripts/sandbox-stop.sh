#!/bin/bash
# Stop sandbox environment

echo "🛑 Stopping sandbox environment..."

docker-compose -f docker-compose.sandbox.yml down

echo "✅ Sandbox environment stopped"



