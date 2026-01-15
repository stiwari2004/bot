#!/bin/bash
# Fix tenant ID sequence issue

echo "=== Current tenants ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug FROM tenants ORDER BY id;"

echo ""
echo "=== Current sequence value ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT last_value, is_called FROM tenants_id_seq;"

echo ""
echo "=== Fixing sequence ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai <<EOF
-- Reset sequence to the maximum ID + 1
SELECT setval('tenants_id_seq', COALESCE((SELECT MAX(id) FROM tenants), 0) + 1, false);
EOF

echo ""
echo "=== New sequence value ==="
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai -c "SELECT last_value, is_called FROM tenants_id_seq;"

echo ""
echo "✅ Sequence fixed! You can now create new tenants."
