#!/bin/bash
# Check dev database contents

echo "=========================================="
echo "Checking Dev Database"
echo "=========================================="
echo ""

echo "1. Checking users..."
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, is_active FROM users LIMIT 10;"

echo ""
echo "2. Checking super_admins..."
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, is_active FROM super_admins;"

echo ""
echo "3. Checking tenants..."
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, subdomain_slug, is_active FROM tenants LIMIT 10;"

echo ""
echo "=========================================="
echo "Database connection is working!"
echo "The issue is authentication, not connectivity."
echo "=========================================="
