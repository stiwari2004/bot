#!/usr/bin/env python3
"""
Create super admin for dev: admin@dev.resolvify.tech
Usage: python scripts/seed_super_admin_dev.py [password]
Default password: Admin123!
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
from app.services.auth import get_password_hash


async def main():
    email = "admin@dev.resolvify.tech"
    password = sys.argv[1] if len(sys.argv) > 1 else "Admin123!"

    await init_db()
    db = SessionLocal()
    try:
        existing = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
        if existing:
            existing.password_hash = get_password_hash(password)
            existing.is_active = True
            db.commit()
            print(f"✅ Super admin {email} (password updated)")
        else:
            sa = SuperAdmin(
                email=email,
                password_hash=get_password_hash(password),
                full_name="Dev Admin",
                is_active=True,
            )
            db.add(sa)
            db.commit()
            db.refresh(sa)
            print(f"✅ Super admin {email} created (ID: {sa.id})")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
