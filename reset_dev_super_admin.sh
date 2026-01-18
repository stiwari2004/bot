#!/bin/bash
# Reset dev super admin password

EMAIL="${1:-admin@dev.resolvify.tech}"
PASSWORD="${2:-S@ndyDemo#2025!}"

echo "=========================================="
echo "Resetting Super Admin Password"
echo "=========================================="
echo "Email: $EMAIL"
echo "Password: [hidden]"
echo ""

# Copy script to container and run it
docker cp reset_dev_super_admin.py bot-dev-backend:/tmp/reset_password.py
docker exec bot-dev-backend python /tmp/reset_password.py "$EMAIL" "$PASSWORD"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Password reset complete!"
    echo ""
    echo "Login credentials:"
    echo "  Email: $EMAIL"
    echo "  Password: [use the password you provided]"
    echo ""
    echo "Try logging in now at: https://dev.resolvify.tech/admin/login"
else
    echo "❌ Failed to reset password"
    exit 1
fi
