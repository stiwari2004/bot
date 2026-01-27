#!/bin/bash
# Create konverge tenant if it doesn't exist

echo "=== Creating 'konverge' Tenant ==="
echo ""

# Check if it already exists
EXISTS=$(docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -t -c "SELECT COUNT(*) FROM tenants WHERE LOWER(subdomain_slug) = 'konverge' OR LOWER(name) = 'konverge';" 2>/dev/null | tr -d ' ')

if [ "$EXISTS" = "0" ]; then
    echo "Creating 'konverge' tenant..."
    docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai << 'EOF'
INSERT INTO tenants (name, subdomain_slug, is_active, deployment_type, platform_managed, created_at)
VALUES ('Konverge', 'konverge', true, 'saas', true, NOW())
ON CONFLICT (name) DO UPDATE SET subdomain_slug = 'konverge', is_active = true
RETURNING id, name, subdomain_slug, is_active;
EOF
    echo ""
    echo "Tenant created successfully!"
else
    echo "Tenant 'konverge' already exists. Showing details:"
    docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active FROM tenants WHERE LOWER(subdomain_slug) = 'konverge' OR LOWER(name) = 'konverge';" 2>/dev/null
fi

echo ""
echo "=== Verifying ==="
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, name, subdomain_slug, is_active FROM tenants ORDER BY id;" 2>/dev/null || echo "Error"
