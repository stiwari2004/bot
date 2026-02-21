#!/usr/bin/env python3
"""
Seed dev database with super admin + default tenant and user.
Usage: python scripts/seed_dev_data.py [super_admin_email] [super_admin_password]
Defaults: admin@dev.resolvify.tech / Admin123!
Also creates: tenant "default", user stiwari2004@gmail.com / S@ndysango1982
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_password_hash


async def main():
    super_email = sys.argv[1] if len(sys.argv) > 1 else "admin@resolvify.tech"
    super_password = sys.argv[2] if len(sys.argv) > 2 else "Admin123!"

    await init_db()
    db = SessionLocal()
    try:
        # 1. Super admin
        sa = db.query(SuperAdmin).filter(SuperAdmin.email == super_email).first()
        if sa:
            sa.password_hash = get_password_hash(super_password)
            sa.is_active = True
            db.commit()
            print(f"✅ Super admin {super_email} (password updated)")
        else:
            sa = SuperAdmin(
                email=super_email,
                password_hash=get_password_hash(super_password),
                full_name="Platform Admin",
                is_active=True,
            )
            db.add(sa)
            db.commit()
            db.refresh(sa)
            print(f"✅ Super admin {super_email} created (ID: {sa.id})")

        # 2. Default tenant
        tenant = db.query(Tenant).filter(Tenant.name == "default").first()
        if not tenant:
            tenant = Tenant(name="default", description="Default tenant for development", is_active=True)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Tenant 'default' created (ID: {tenant.id})")
        else:
            print(f"   Tenant 'default' exists (ID: {tenant.id})")

        # 3. Default user (for normal login)
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                full_name="Admin User",
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ User admin@example.com created (ID: {user.id})")
        else:
            print(f"   User admin@example.com exists (ID: {user.id})")

        print("\n--- Dev login credentials ---")
        print("Super admin:", super_email, "/", super_password)
        print("Normal user: admin@example.com / admin123")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
