#!/usr/bin/env python3
"""Script to check and fix user account"""
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.services.auth import get_password_hash
from sqlalchemy import func
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: python check_user.py <email> [new_password]")
    sys.exit(1)

email = sys.argv[1]
new_password = sys.argv[2] if len(sys.argv) > 2 else None

db = SessionLocal()
try:
    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    if not user:
        print(f"User with email {email} not found")
        sys.exit(1)
    
    print(f"User found: {user.email}")
    print(f"  ID: {user.id}")
    print(f"  Is active: {user.is_active}")
    print(f"  Locked until: {user.locked_until}")
    print(f"  Failed attempts: {user.failed_login_attempts or 0}")
    print(f"  Has password hash: {bool(user.password_hash)}")
    print(f"  Password hash length: {len(user.password_hash) if user.password_hash else 0}")
    if user.password_hash:
        print(f"  Password hash prefix: {user.password_hash[:30]}...")
    
    if new_password:
        print(f"\nResetting password for {email}...")
        user.password_hash = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.must_change_password = False
        db.commit()
        print(f"Password reset successful! New password: {new_password}")
    elif user.locked_until and user.locked_until > datetime.utcnow():
        print(f"\nAccount is locked until {user.locked_until}")
        print("To unlock, run: python check_user.py <email> <new_password>")
    elif user.failed_login_attempts and user.failed_login_attempts > 0:
        print(f"\nAccount has {user.failed_login_attempts} failed attempts")
        print("To reset, run: python check_user.py <email> <new_password>")
finally:
    db.close()

