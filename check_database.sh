#!/bin/bash
# Script to check database status and users
echo "=== Checking PostgreSQL Connection ==="
docker exec bot-dev-postgres psql -U postgres -c "\l" 2>/dev/null || echo "Cannot connect to postgres"

echo ""
echo "=== Checking Database: troubleshooting_ai_dev ==="
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\dt" 2>/dev/null || echo "Cannot list tables"

echo ""
echo "=== Checking Users Table ==="
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, is_active, tenant_id FROM users LIMIT 20;" 2>/dev/null || echo "Cannot query users"

echo ""
echo "=== Checking Tenants Table ==="
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, is_msp, is_active FROM tenants;" 2>/dev/null || echo "Cannot query tenants"

echo ""
echo "=== Checking Super Admins Table ==="
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, is_active FROM super_admins;" 2>/dev/null || echo "Cannot query super_admins"

