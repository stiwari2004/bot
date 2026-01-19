#!/bin/bash
# Check super admin password hash in database

echo "🔍 Checking super admin password in database..."

docker exec -it bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "
SELECT 
    id,
    email,
    CASE 
        WHEN password_hash IS NULL THEN 'NULL'
        WHEN password_hash = '' THEN 'EMPTY'
        ELSE SUBSTRING(password_hash, 1, 50) || '...'
    END as password_hash_preview,
    LENGTH(password_hash) as hash_length,
    is_active,
    created_at
FROM super_admins
WHERE email = 'admin@dev.resolvify.tech';
"

echo ""
echo "📋 To reset the password, use:"
echo "   python reset_dev_super_admin.py"
