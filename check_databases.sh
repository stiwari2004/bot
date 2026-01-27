#!/bin/bash
# Check all databases and their users to identify duplicates

echo "=== Checking All PostgreSQL Containers ==="
echo ""

# List all postgres containers
echo "1. Finding all PostgreSQL containers..."
docker ps -a --filter "ancestor=pgvector/pgvector:pg15" --format "{{.Names}}\t{{.Status}}"
docker ps -a --filter "name=postgres" --format "{{.Names}}\t{{.Status}}"

echo ""
echo "=== Checking bot-prod-postgres (Production) ==="
if docker ps -a --format "{{.Names}}" | grep -q "^bot-prod-postgres$"; then
    echo "Container exists. Checking databases..."
    echo ""
    echo "All databases in bot-prod-postgres:"
    docker exec bot-prod-postgres psql -U postgres -c "\l" 2>/dev/null || echo "Container not running or error"
    echo ""
    echo "Users in troubleshooting_ai database:"
    docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Database doesn't exist or error"
    echo ""
    echo "Total super_admin users:"
    docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total FROM users WHERE role = 'super_admin';" 2>/dev/null || echo "Error"
else
    echo "Container bot-prod-postgres not found"
fi

echo ""
echo "=== Checking bot-dev-postgres (Development) ==="
if docker ps -a --format "{{.Names}}" | grep -q "^bot-dev-postgres$"; then
    echo "Container exists. Checking databases..."
    echo ""
    echo "All databases in bot-dev-postgres:"
    docker exec bot-dev-postgres psql -U postgres -c "\l" 2>/dev/null || echo "Container not running or error"
    echo ""
    echo "Users in troubleshooting_ai_dev database:"
    docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, tenant_id FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Database doesn't exist or error"
    echo ""
    echo "Total super_admin users:"
    docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT COUNT(*) as total FROM users WHERE role = 'super_admin';" 2>/dev/null || echo "Error"
    
    echo ""
    echo "Checking if troubleshooting_ai (without _dev) exists in dev container:"
    docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Database troubleshooting_ai doesn't exist in dev container"
else
    echo "Container bot-dev-postgres not found"
fi

echo ""
echo "=== Checking for other PostgreSQL containers ==="
for container in $(docker ps -a --format "{{.Names}}" | grep -i postgres); do
    if [ "$container" != "bot-prod-postgres" ] && [ "$container" != "bot-dev-postgres" ]; then
        echo ""
        echo "Found other container: $container"
        echo "Status: $(docker ps -a --filter "name=$container" --format '{{.Status}}')"
        echo "Databases:"
        docker exec $container psql -U postgres -c "\l" 2>/dev/null || echo "Cannot access container"
    fi
done

echo ""
echo "=== Checking backend container database connections ==="
if docker ps --format "{{.Names}}" | grep -q "^bot-prod-backend$"; then
    echo "Production backend DATABASE_URL:"
    docker exec bot-prod-backend env | grep DATABASE_URL || echo "Not found"
fi

if docker ps --format "{{.Names}}" | grep -q "^bot-dev-backend$"; then
    echo "Development backend DATABASE_URL:"
    docker exec bot-dev-backend env | grep DATABASE_URL || echo "Not found"
fi

echo ""
echo "=== Summary ==="
echo "Run this script to see all databases and their super_admin user counts"
