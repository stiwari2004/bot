#!/usr/bin/env python3
"""
Seed dev database with super admin + default tenant + tenant admin and user.
Usage: python scripts/seed_dev_data.py [super_admin_email] [super_admin_password]
Defaults: admin@dev.resolvify.tech / Admin@123!
Creates: super admin, tenant (demo/default if missing), tenant admin user, optional dev user.
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

DEFAULT_SUPER_EMAIL = "admin@dev.resolvify.tech"
DEFAULT_SUPER_PASSWORD = "Admin@123!"


def ensure_user(db, tenant_id: int, email: str, password: str, full_name: str, role: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ User {email} created (ID: {user.id}, role={role})")
    else:
        user.password_hash = get_password_hash(password)
        user.is_active = True
        db.commit()
        print(f"   User {email} exists (ID: {user.id}), password updated")
    return user


async def main():
    super_email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUPER_EMAIL
    super_password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SUPER_PASSWORD

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

        # 2. Tenant (use demo id=1 or default)
        tenant = db.query(Tenant).filter(Tenant.id == 1).first() or db.query(Tenant).filter(Tenant.name == "default").first()
        if not tenant:
            tenant = Tenant(name="default", description="Default tenant for development", is_active=True)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Tenant 'default' created (ID: {tenant.id})")
        else:
            print(f"   Tenant '{tenant.name}' exists (ID: {tenant.id})")

        # 3. Tenant admin (same email as super admin for dev convenience)
        ensure_user(db, tenant.id, super_email, super_password, "Tenant Admin", "admin")

        # 4. Optional dev user (for normal login)
        ensure_user(db, tenant.id, "dev@dev.resolvify.tech", super_password, "Dev User", "user")

        print("\n--- Dev login credentials ---")
        print("Super admin (use at /super-admin/login):", super_email, "/", super_password)
        print("Tenant admin / user (use at /):", super_email, "/", super_password)
        print("Regular user:", "dev@dev.resolvify.tech", "/", super_password)
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
