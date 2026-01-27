#!/bin/bash
# Check for duplicate super_admin users with admin@resolvify.tech

echo "=== Checking for Duplicate Super Admin Users ==="
echo ""

# Check production database
echo "=== PRODUCTION DATABASE (bot-prod-postgres) ==="
echo ""
echo "All super_admin users:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id, is_active, created_at FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Error accessing production database"

echo ""
echo "Users with email admin@resolvify.tech (case-insensitive):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id, is_active, created_at FROM users WHERE LOWER(email) = 'admin@resolvify.tech' ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "Tenant associations for admin@resolvify.tech users:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT u.id as user_id, u.email, u.tenant_id, t.id as tenant_id_db, t.name as tenant_name, t.subdomain_slug 
FROM users u 
LEFT JOIN tenants t ON u.tenant_id = t.id 
WHERE LOWER(u.email) = 'admin@resolvify.tech' 
ORDER BY u.id;
" 2>/dev/null || echo "Error"

echo ""
echo "Count of tenants associated with admin@resolvify.tech users:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT u.id as user_id, COUNT(DISTINCT u.tenant_id) as tenant_count
FROM users u 
WHERE LOWER(u.email) = 'admin@resolvify.tech' 
GROUP BY u.id;
" 2>/dev/null || echo "Error"

echo ""
echo "=== Checking tenant 'konverge' ==="
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active 
FROM tenants 
WHERE LOWER(name) LIKE '%konverge%' OR LOWER(subdomain_slug) = 'konverge';
" 2>/dev/null || echo "Error"

echo ""
echo "=== DEVELOPMENT DATABASE (bot-dev-postgres) ==="
echo ""
echo "All super_admin users:"
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, tenant_id, is_active, created_at FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Error accessing dev database"

echo ""
echo "Users with email admin@resolvify.tech:"
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, tenant_id, is_active, created_at FROM users WHERE LOWER(email) = 'admin@resolvify.tech' ORDER BY id;" 2>/dev/null || echo "Error"
