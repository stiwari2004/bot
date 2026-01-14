#!/bin/bash
# Script to create user directly in database
# This generates the password hash and creates the user

EMAIL="${1:-admin@dev.resolvify.tech}"
PASSWORD="${2:-admin123}"
TENANT_ID="${3:-1}"

# Generate password hash using Python (pbkdf2_sha256)
HASH=$(docker exec bot-dev-backend python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
print(pwd_context.hash('$PASSWORD'))
")

if [ -z "$HASH" ]; then
    echo "Failed to generate password hash"
    exit 1
fi

echo "Creating user: $EMAIL"
echo "Password hash: ${HASH:0:50}..."

# Get postgres container ID
PG_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')

if [ -z "$PG_CONTAINER" ]; then
    echo "PostgreSQL container not found!"
    exit 1
fi

# Create user
docker exec $PG_CONTAINER psql -U postgres -d troubleshooting_ai_dev << EOF
-- Insert user (update if exists)
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, created_at, updated_at, failed_login_attempts, locked_until)
VALUES (
    $TENANT_ID,
    '$EMAIL',
    '$HASH',
    'Admin User',
    'admin',
    true,
    NOW(),
    NOW(),
    0,
    NULL
)
ON CONFLICT (email) 
DO UPDATE SET 
    password_hash = EXCLUDED.password_hash,
    failed_login_attempts = 0,
    locked_until = NULL,
    is_active = true,
    updated_at = NOW();

-- Verify user was created
SELECT id, email, role, is_active, tenant_id FROM users WHERE email = '$EMAIL';
EOF

echo ""
echo "✅ User created/updated: $EMAIL"
echo "   Password: $PASSWORD"
echo "   Tenant ID: $TENANT_ID"

