# Quick Password Reset for Dev Super Admin

## Option 1: Direct Python Command (Easiest)

Run this on your server:

```bash
docker exec bot-dev-backend python -c "
import sys
sys.path.insert(0, '/app')
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from app.core.config import settings

email = 'admin@dev.resolvify.tech'
password = 'S@ndyDemo#2025!'

ctx = CryptContext(schemes=['pbkdf2_sha256'])
hash_value = ctx.hash(password)

db_url = settings.DATABASE_URL
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute(
        text('UPDATE super_admins SET password_hash = :hash WHERE email = :email'),
        {'hash': hash_value, 'email': email}
    )
    conn.commit()
    print('SUCCESS: Password reset for', email) if result.rowcount > 0 else print('ERROR: No rows updated')
"
```

## Option 2: Using the Script

```bash
# Copy script to container
docker cp reset_dev_super_admin.py bot-dev-backend:/tmp/

# Run it
docker exec bot-dev-backend python /tmp/reset_dev_super_admin.py admin@dev.resolvify.tech 'S@ndyDemo#2025!'
```

## Option 3: Direct SQL (if you know the hash)

```bash
# Generate hash first
HASH=$(docker exec bot-dev-backend python -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['pbkdf2_sha256']); print(ctx.hash('S@ndyDemo#2025!'))")

# Update database
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "UPDATE super_admins SET password_hash = '$HASH' WHERE email = 'admin@dev.resolvify.tech';"
```

## Verify Password Works

After resetting, test the password:

```bash
docker exec bot-dev-backend python -c "
import sys
sys.path.insert(0, '/app')
from app.services.super_admin_auth import authenticate_super_admin
from app.core.database import SessionLocal

db = SessionLocal()
result = authenticate_super_admin(db, 'admin@dev.resolvify.tech', 'S@ndyDemo#2025!')
print('✅ Login works!' if result else '❌ Login failed')
db.close()
"
```
