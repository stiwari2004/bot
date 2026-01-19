#!/bin/bash
# Reset super admin password directly in the database

EMAIL="${1:-admin@dev.resolvify.tech}"
PASSWORD="${2:-S@ndysango1982}"

echo "🔐 Resetting super admin password..."
echo "Email: $EMAIL"
echo ""

# Generate password hash using the backend container
echo "Generating password hash..."
HASH=$(docker exec -i bot-dev-backend python -c "
import sys
sys.path.insert(0, '/app')
from app.services.auth import get_password_hash
print(get_password_hash('$PASSWORD'))
")

if [ -z "$HASH" ]; then
    echo "❌ Failed to generate password hash"
    exit 1
fi

echo "Hash generated: ${HASH:0:50}..."
echo ""

# Update database
echo "Updating database..."
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev <<EOF
UPDATE super_admins 
SET password_hash = '$HASH', updated_at = NOW()
WHERE email = '$EMAIL';

SELECT 
    email,
    CASE WHEN password_hash IS NOT NULL THEN 'Password updated' ELSE 'ERROR: No hash' END as status,
    LENGTH(password_hash) as hash_length
FROM super_admins
WHERE email = '$EMAIL';
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Password reset successful!"
    echo ""
    echo "Test login with:"
    echo "  curl -4 -X POST http://localhost:8001/api/v1/super-admin/auth/login \\"
    echo "    -H 'Content-Type: application/x-www-form-urlencoded' \\"
    echo "    -d 'username=$EMAIL&password=$PASSWORD'"
else
    echo "❌ Failed to update password"
    exit 1
fi
