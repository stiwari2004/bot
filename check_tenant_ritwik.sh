#!/bin/bash
# Check if tenant "ritwik" exists

echo "=== Checking for tenant 'ritwik' ==="

# Check by subdomain_slug (case-insensitive)
echo ""
echo "1. By subdomain_slug (case-insensitive):"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active, deployment_type, is_msp, created_at 
FROM tenants 
WHERE LOWER(subdomain_slug) = LOWER('ritwik');
"

# Check by name
echo ""
echo "2. By name (case-insensitive):"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active, deployment_type, is_msp, created_at 
FROM tenants 
WHERE LOWER(name) = LOWER('Ritwik');
"

# Check all tenants
echo ""
echo "3. All tenants:"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active, deployment_type, is_msp 
FROM tenants 
ORDER BY id;
"

# Check sequence
echo ""
echo "4. Current sequence value:"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT last_value, is_called FROM tenants_id_seq;
"

echo ""
echo "=== Analysis ==="
echo "If tenant exists but creation fails, the duplicate check might not be working."
echo "If tenant doesn't exist, the sequence needs to be fixed."
