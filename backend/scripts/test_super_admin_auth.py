#!/usr/bin/env python3
"""
Test super admin authentication
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
from app.services.auth import verify_password, get_password_hash
from app.services.super_admin_auth import authenticate_super_admin

async def test_auth():
    await init_db()
    db = SessionLocal()
    try:
        email = 'admin@dev.resolvify.tech'
        password = 'dev123'
        
        # Check if super admin exists
        super_admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        if not super_admin:
            print(f"❌ Super admin {email} not found")
            return
        
        print(f"✅ Found super admin:")
        print(f"   ID: {super_admin.id}")
        print(f"   Email: {super_admin.email}")
        print(f"   Full Name: {super_admin.full_name}")
        print(f"   Active: {super_admin.is_active}")
        print(f"   Password Hash: {super_admin.password_hash[:50]}...")
        
        # Test password verification
        print(f"\n🔐 Testing password verification...")
        is_valid = verify_password(password, super_admin.password_hash)
        print(f"   Password 'dev123' is valid: {is_valid}")
        
        if not is_valid:
            print(f"\n⚠️  Password verification failed!")
            print(f"   Generating new hash for 'dev123'...")
            new_hash = get_password_hash(password)
            print(f"   New hash: {new_hash[:50]}...")
            print(f"   Verifying new hash: {verify_password(password, new_hash)}")
        
        # Test authentication function
        print(f"\n🔑 Testing authenticate_super_admin function...")
        authenticated = authenticate_super_admin(db, email, password)
        if authenticated:
            print(f"   ✅ Authentication successful!")
            print(f"   Authenticated admin ID: {authenticated.id}")
        else:
            print(f"   ❌ Authentication failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_auth())

