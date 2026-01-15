#!/bin/bash
# Test super admin password validation

PASSWORD="S@ndyDemo#2025!"

echo "=== Testing Password: $PASSWORD ==="
echo ""

echo "1. Testing password policy validation..."
docker exec bot-prod_backend_1 python -c "
from app.core.password_policy import PasswordPolicy

password = 'S@ndyDemo#2025!'
email = 'admin@resolvify.tech'

is_valid, errors = PasswordPolicy.validate_password(password, email)
if is_valid:
    print('✅ Password passes policy validation')
else:
    print('❌ Password fails policy validation:')
    for error in errors:
        print(f'   - {error}')
" 2>&1

echo ""
echo "2. Testing password hash generation..."
docker exec bot-prod_backend_1 python -c "
from passlib.context import CryptContext

ctx = CryptContext(schemes=['pbkdf2_sha256'])
password = 'S@ndyDemo#2025!'
hash_result = ctx.hash(password)
print(f'✅ Hash generated: {hash_result[:50]}...')
print(f'   Length: {len(hash_result)}')
" 2>&1

echo ""
echo "3. Testing password verification..."
docker exec bot-prod_backend_1 python -c "
from passlib.context import CryptContext
from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin

ctx = CryptContext(schemes=['pbkdf2_sha256'])
password = 'S@ndyDemo#2025!'

db = SessionLocal()
try:
    admin = db.query(SuperAdmin).first()
    if admin:
        print(f'Found super admin: {admin.email}')
        print(f'Hash in DB: {admin.password_hash[:50]}...')
        
        # Test verification
        is_valid = ctx.verify(password, admin.password_hash)
        if is_valid:
            print('✅ Password verification: SUCCESS')
        else:
            print('❌ Password verification: FAILED')
            print('   This means the password hash in DB does not match the password')
    else:
        print('❌ No super admin found in database')
finally:
    db.close()
" 2>&1
