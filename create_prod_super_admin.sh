#!/bin/bash
# Create super admin in production database

set -e

EMAIL="${1:-admin@resolvify.tech}"
PASSWORD="${2:-S@ndyDemo#2025!}"

echo "Creating super admin: $EMAIL"

# Generate password hash
echo "Generating password hash..."
PASSWORD_HASH=$(docker exec bot-prod_backend_1 python -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['pbkdf2_sha256']); print(ctx.hash('$PASSWORD'))")

if [ -z "$PASSWORD_HASH" ]; then
    echo "❌ Failed to generate password hash"
    exit 1
fi

echo "Hash generated: ${PASSWORD_HASH:0:50}..."

# Create super admin
echo "Creating super admin in database..."
docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai <<EOF
INSERT INTO super_admins (email, password_hash, full_name, is_active, created_at, updated_at)
VALUES (
  '$EMAIL',
  '$PASSWORD_HASH',
  'Super Admin',
  true,
  NOW(),
  NOW()
) ON CONFLICT (email) DO UPDATE 
SET 
  password_hash = EXCLUDED.password_hash,
  is_active = true,
  updated_at = NOW();

-- Verify
SELECT id, email, is_active, created_at FROM super_admins WHERE email = '$EMAIL';
EOF

echo ""
echo "✅ Super admin created/updated!"
echo "   Email: $EMAIL"
echo "   Password: $PASSWORD"
echo ""
echo "Test login with:"
echo "  curl -X POST 'https://admin.resolvify.tech/api/v1/super-admin/auth/login' \\"
echo "    -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "    -d 'username=$EMAIL&password=$PASSWORD'"
