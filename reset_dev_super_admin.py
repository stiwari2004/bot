#!/usr/bin/env python3
"""
Reset dev super admin password
Usage: docker exec bot-dev-backend python /app/reset_dev_super_admin.py <email> <password>
"""
import sys
import os

# Add app to path
sys.path.insert(0, '/app')

from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_password(email: str, password: str):
    """Reset super admin password"""
    # Generate hash
    ctx = CryptContext(schemes=['pbkdf2_sha256'])
    hash_value = ctx.hash(password)
    
    print(f"Resetting password for: {email}")
    print(f"Hash: {hash_value[:50]}...")
    
    # Update database
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(
            text('UPDATE super_admins SET password_hash = :hash WHERE email = :email'),
            {'hash': hash_value, 'email': email}
        )
        conn.commit()
        if result.rowcount > 0:
            print(f"✅ Password reset successful for {email}")
            return True
        else:
            print(f"❌ No super admin found with email: {email}")
            return False

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@dev.resolvify.tech"
    password = sys.argv[2] if len(sys.argv) > 2 else "S@ndyDemo#2025!"
    
    success = reset_password(email, password)
    sys.exit(0 if success else 1)
