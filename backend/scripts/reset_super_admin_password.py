#!/usr/bin/env python3
"""
Script to reset super admin password or create one if it doesn't exist
Usage: python scripts/reset_super_admin_password.py <email> <new_password>
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
from app.services.auth import get_password_hash
from app.core.logging import get_logger

logger = get_logger(__name__)


async def reset_super_admin_password(email: str, password: str):
    """Reset super admin password or create one if it doesn't exist"""
    await init_db()
    db = SessionLocal()
    
    try:
        # Check if super admin exists
        super_admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        
        if super_admin:
            # Update existing super admin password
            super_admin.password_hash = get_password_hash(password)
            db.commit()
            print(f"✅ Password reset for super admin: {email}")
        else:
            # Create new super admin
            super_admin = SuperAdmin(
                email=email,
                password_hash=get_password_hash(password),
                full_name="Super Admin",
                is_active=True
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"✅ Created new super admin: {email}")
        
        print(f"\nLogin credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"\nLogin URL: http://localhost:8000/api/v1/super-admin/auth/login")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/reset_super_admin_password.py <email> <password>")
        print("Example: python scripts/reset_super_admin_password.py admin@platform.com admin123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    asyncio.run(reset_super_admin_password(email, password))

