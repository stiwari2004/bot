#!/bin/bash
# Create demo user in production database

set -e

PASSWORD_HASH="$1"

if [ -z "$PASSWORD_HASH" ]; then
    echo "Generating password hash for 'demo123'..."
    PASSWORD_HASH=$(docker exec bot-prod_backend_1 python -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['pbkdf2_sha256']); print(ctx.hash('demo123'))")
    echo "Generated hash: ${PASSWORD_HASH:0:50}..."
fi

echo "Creating/updating demo user in production database..."

docker exec bot-prod_postgres_1 psql -U postgres -d troubleshooting_ai <<EOF
-- Ensure tenant exists
INSERT INTO tenants (id, name, is_msp, is_active, created_at, updated_at)
VALUES (1, 'demo', false, true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET is_active = true;

-- Create/update demo user
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, created_at, updated_at)
VALUES (
  1,
  'demo@example.com',
  '$PASSWORD_HASH',
  'Demo User',
  'user',
  true,
  NOW(),
  NOW()
) ON CONFLICT (email) DO UPDATE 
SET 
  password_hash = EXCLUDED.password_hash,
  is_active = true,
  updated_at = NOW();

-- Verify user was created
SELECT id, email, role, is_active, tenant_id FROM users WHERE email = 'demo@example.com';
EOF

echo ""
echo "✅ Demo user created/updated!"
echo "   Email: demo@example.com"
echo "   Password: demo123"
