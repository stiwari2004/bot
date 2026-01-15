#!/bin/bash
# Check if tenant already exists

SUBDOMAIN="${1:-ritwik}"

echo "=== Checking for tenant with subdomain: $SUBDOMAIN ==="

# Check in production database
echo ""
echo "1. Production database (troubleshooting_ai):"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active, deployment_type, is_msp 
FROM tenants 
WHERE subdomain_slug = '$SUBDOMAIN' OR name ILIKE '%$SUBDOMAIN%';
"

# Check all tenants
echo ""
echo "2. All tenants in production:"
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "
SELECT id, name, subdomain_slug, is_active, deployment_type, is_msp, created_at 
FROM tenants 
ORDER BY id;
"

# Check tenant creation endpoint logic
echo ""
echo "3. Checking tenant creation code..."
echo "   (This will show if there's a duplicate check)"
