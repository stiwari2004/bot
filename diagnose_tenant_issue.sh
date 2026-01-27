#!/bin/bash
# Comprehensive diagnostic for tenant/login issue

echo "=== COMPREHENSIVE TENANT/LOGIN DIAGNOSTIC ==="
echo ""

echo "=== 1. PRODUCTION DATABASE STATE ==="
echo ""
echo "Tenants:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active, created_at FROM tenants ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "Users:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id, is_active FROM users ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "Super Admins:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, is_active, created_at FROM super_admins ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "=== 2. CHECKING FOR 'konverge' TENANT ==="
echo ""
echo "By name:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug FROM tenants WHERE LOWER(name) LIKE '%konverge%';" 2>/dev/null || echo "Error"

echo ""
echo "By slug:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug FROM tenants WHERE LOWER(subdomain_slug) = 'konverge';" 2>/dev/null || echo "Error"

echo ""
echo "=== 3. DASHBOARD COUNTS (what super admin sees) ==="
echo ""
echo "Total tenants:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total FROM tenants;" 2>/dev/null || echo "Error"

echo ""
echo "Total users:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total FROM users;" 2>/dev/null || echo "Error"

echo ""
echo "=== 4. CHECKING IF 'konverge' TENANT SHOULD EXIST ==="
echo ""
echo "Checking for any references to 'konverge' in database:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT 'tenants' as table_name, id, name, subdomain_slug 
FROM tenants 
WHERE LOWER(name) LIKE '%konverge%' OR LOWER(subdomain_slug) LIKE '%konverge%'
UNION ALL
SELECT 'users' as table_name, id, email as name, NULL as subdomain_slug
FROM users 
WHERE LOWER(email) LIKE '%konverge%';
" 2>/dev/null || echo "Error"

echo ""
echo "=== 5. RECOMMENDATION ==="
echo ""
echo "If 'konverge' tenant should exist, create it with:"
echo "docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c \""
echo "INSERT INTO tenants (name, subdomain_slug, is_active, deployment_type, platform_managed) "
echo "VALUES ('Konverge', 'konverge', true, 'saas', true) "
echo "ON CONFLICT (name) DO NOTHING "
echo "RETURNING id, name, subdomain_slug;"
echo "\""
