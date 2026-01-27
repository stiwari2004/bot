#!/bin/bash
# Check all users and their roles to understand the data structure

echo "=== Checking All Users in Production Database ==="
echo ""

echo "1. All users (first 20):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, role_id, tenant_id, is_active, created_at FROM users ORDER BY id LIMIT 20;" 2>/dev/null || echo "Error"

echo ""
echo "2. Total user count:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total_users FROM users;" 2>/dev/null || echo "Error"

echo ""
echo "3. All distinct roles:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT DISTINCT role FROM users WHERE role IS NOT NULL ORDER BY role;" 2>/dev/null || echo "Error"

echo ""
echo "4. Users with admin@resolvify.tech (any case):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, role_id, tenant_id, is_active FROM users WHERE LOWER(email) LIKE '%admin%resolvify%' ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "5. Check if roles table exists and what it contains:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, description FROM roles LIMIT 10;" 2>/dev/null || echo "Roles table doesn't exist or error"

echo ""
echo "6. Users with role_id (RBAC system):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT u.id, u.email, u.role, u.role_id, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.role_id IS NOT NULL LIMIT 10;" 2>/dev/null || echo "Error"

echo ""
echo "7. All tenants:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active FROM tenants ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "8. Users per tenant:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT t.id, t.name, t.subdomain_slug, COUNT(u.id) as user_count FROM tenants t LEFT JOIN users u ON t.id = u.tenant_id GROUP BY t.id, t.name, t.subdomain_slug ORDER BY t.id;" 2>/dev/null || echo "Error"

echo ""
echo "9. Check if super_admins table exists:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "\d super_admins" 2>/dev/null || echo "super_admins table doesn't exist"

echo ""
echo "10. All super_admins (if table exists):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT * FROM super_admins LIMIT 20;" 2>/dev/null || echo "super_admins table doesn't exist or error"

echo ""
echo "11. Check all tables in database:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "\dt" | grep -i "user\|admin\|tenant" 2>/dev/null || echo "Error listing tables"
