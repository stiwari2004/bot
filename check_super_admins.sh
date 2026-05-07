#!/bin/bash
# Check super_admins table for duplicate admin@resolvify.tech entries

echo "=== Checking super_admins Table ==="
echo ""

echo "=== PRODUCTION DATABASE (bot-prod-postgres) ==="
echo ""
echo "1. All super_admins:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, full_name, is_active, created_at FROM super_admins ORDER BY id;" 2>/dev/null || echo "Error or table doesn't exist"

echo ""
echo "2. Super_admins with email admin@resolvify.tech (case-insensitive):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, full_name, is_active, created_at FROM super_admins WHERE LOWER(email) = 'admin@resolvify.tech' ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "3. Count of super_admins:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total FROM super_admins;" 2>/dev/null || echo "Error"

echo ""
echo "=== Checking users table for super_admin role ==="
echo ""
echo "4. Users with role = 'super_admin':"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, role_id, tenant_id, is_active FROM users WHERE role = 'super_admin' ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "5. Users with admin@resolvify.tech in users table:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, role_id, tenant_id, is_active FROM users WHERE LOWER(email) = 'admin@resolvify.tech' ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "=== Checking tenants ==="
echo ""
echo "6. All tenants:"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active FROM tenants ORDER BY id;" 2>/dev/null || echo "Error"

echo ""
echo "7. Tenant 'konverge' (by slug):"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active FROM tenants WHERE LOWER(subdomain_slug) = 'konverge' OR LOWER(name) LIKE '%konverge%';" 2>/dev/null || echo "Error"

echo ""
echo "=== DEVELOPMENT DATABASE (bot-dev-postgres) ==="
echo ""
echo "8. All super_admins in dev:"
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, full_name, is_active, created_at FROM super_admins ORDER BY id;" 2>/dev/null || echo "Error or table doesn't exist"

echo ""
echo "9. Super_admins with admin@resolvify.tech in dev:"
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, full_name, is_active, created_at FROM super_admins WHERE LOWER(email) = 'admin@resolvify.tech' ORDER BY id;" 2>/dev/null || echo "Error"
