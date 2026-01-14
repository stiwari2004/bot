#!/usr/bin/env python3
"""Script to create super admin"""
import sys
import os
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.super_admin import SuperAdmin
from app.services.auth import get_password_hash

def main():
    email = sys.argv[1] if len(sys.argv) > 1 else 'admin@dev.resolvify.tech'
    password = sys.argv[2] if len(sys.argv) > 2 else 'admin123'
    
    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        if existing:
            print(f"Super admin {email} already exists, updating password...")
            existing.password_hash = get_password_hash(password)
            existing.is_active = True
            existing.full_name = existing.full_name or 'Super Admin'
        else:
            print(f"Creating super admin {email}...")
            super_admin = SuperAdmin(
                email=email,
                password_hash=get_password_hash(password),
                full_name='Super Admin',
                is_active=True
            )
            db.add(super_admin)
        
        db.commit()
        print(f"✅ Super admin created/updated: {email}")
        print(f"   Password: {password}")
        
        # Verify
        admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        if admin:
            print(f"   ID: {admin.id}")
            print(f"   Active: {admin.is_active}")
            print(f"   Full Name: {admin.full_name}")
        else:
            print("❌ Failed to create super admin")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

