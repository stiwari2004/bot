#!/usr/bin/env python3
"""
Non-interactive script to create or update a super admin user
Usage: python scripts/create_super_admin_noninteractive.py <email> <password> [full_name]
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
from app.services.auth import get_password_hash
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_super_admin(email: str, password: str, full_name: str = None):
    """Create or update a super admin user (non-interactive)"""

    # Initialize database
    await init_db()

    db = SessionLocal()
    try:
        # Check if super admin already exists
        existing = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        if existing:
            print(f"⚠️  Super admin with email {email} already exists - updating password")
            existing.password_hash = get_password_hash(password)
            if full_name:
                existing.full_name = full_name
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            print(f"✅ Updated super admin {email}")
            print(f"   ID: {existing.id}")
            print(f"   Full Name: {existing.full_name or 'N/A'}")
            print(f"   Active: {existing.is_active}")
            return True

        # Create new super admin
        super_admin = SuperAdmin(
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            is_active=True,
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        print(f"✅ Created super admin {email}")
        print(f"   ID: {super_admin.id}")
        print(f"   Full Name: {super_admin.full_name or 'N/A'}")
        print(f"   Active: {super_admin.is_active}")
        return True

    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/create_super_admin_noninteractive.py <email> <password> [full_name]")
        print("Example: python scripts/create_super_admin_noninteractive.py admin@platform.com admin123 \"Platform Admin\"")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else None

    asyncio.run(create_super_admin(email, password, full_name))

