#!/usr/bin/env python3
"""
Script to create an admin user
Usage: python scripts/create_admin_user.py [email] [password] [tenant_name]
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_password_hash


async def create_admin_user(email: str = "admin@example.com", password: str = "admin123", tenant_id: int = None):
    """Create an admin user in an existing tenant"""
    
    # Initialize database
    await init_db()
    
    db = SessionLocal()
    try:
        # Get tenant - use tenant_id if provided, otherwise try to find by name or use ID 1
        if tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        else:
            # Try to find "default" tenant, or "demo" tenant, or use ID 1
            tenant = db.query(Tenant).filter(Tenant.name == "default").first()
            if not tenant:
                tenant = db.query(Tenant).filter(Tenant.name == "demo").first()
            if not tenant:
                tenant = db.query(Tenant).filter(Tenant.id == 1).first()
        
        if not tenant:
            # Create default tenant if none exists
            tenant = Tenant(
                id=1,
                name="default",
                description="Default tenant",
                is_active=True
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Created tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"✅ Using existing tenant: {tenant.name} (ID: {tenant.id})")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # Update to admin if not already
            if existing_user.role != "admin":
                existing_user.role = "admin"
                db.commit()
                print(f"✅ Updated user {email} to admin role")
            else:
                print(f"✅ User {email} already exists with admin role")
            print(f"   Password: {password}")
            return existing_user
        
        # Create admin user
        admin_user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=get_password_hash(password),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Created admin user:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Tenant: {tenant.name} (ID: {tenant.id})")
        print(f"   User ID: {admin_user.id}")
        print(f"\n🔐 Login at: POST http://localhost:8000/api/v1/auth/login")
        print(f"   Body: username={email}&password={password}")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio
    
    # Get arguments
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    tenant_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
    
    print(f"Creating admin user...")
    print(f"Email: {email}")
    if tenant_id:
        print(f"Tenant ID: {tenant_id}")
    print()
    
    asyncio.run(create_admin_user(email, password, tenant_id))

