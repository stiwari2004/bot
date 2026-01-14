#!/usr/bin/env python3
"""Quick script to check database and create user"""
import sys
import os
sys.path.insert(0, '/app')

from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_password_hash
from sqlalchemy import func
import asyncio

async def main():
    # Initialize database (creates tables if needed)
    await init_db()
    
    db = SessionLocal()
    try:
        # Check tenants
        tenants = db.query(Tenant).all()
        print(f"Found {len(tenants)} tenants:")
        for t in tenants:
            print(f"  ID: {t.id}, Name: {t.name}, Active: {t.is_active}")
        
        # Get or create demo tenant
        demo_tenant = db.query(Tenant).filter(Tenant.id == 1).first()
        if not demo_tenant:
            demo_tenant = Tenant(id=1, name="demo", description="Demo tenant", is_active=True)
            db.add(demo_tenant)
            db.commit()
            print(f"Created demo tenant")
        
        # Check users
        users = db.query(User).all()
        print(f"\nFound {len(users)} users:")
        for u in users:
            print(f"  ID: {u.id}, Email: {u.email}, Role: {u.role}, Active: {u.is_active}")
        
        # Create user if email provided
        if len(sys.argv) >= 3:
            email = sys.argv[1]
            password = sys.argv[2]
            role = sys.argv[3] if len(sys.argv) > 3 else "admin"
            
            existing = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
            if existing:
                print(f"\nUser {email} already exists!")
                print(f"  ID: {existing.id}, Role: {existing.role}")
                # Reset password
                existing.password_hash = get_password_hash(password)
                existing.failed_login_attempts = 0
                existing.locked_until = None
                existing.is_active = True
                db.commit()
                print(f"✅ Password reset for {email}")
            else:
                user = User(
                    tenant_id=demo_tenant.id,
                    email=email,
                    password_hash=get_password_hash(password),
                    full_name=email.split("@")[0].title(),
                    role=role,
                    is_active=True
                )
                db.add(user)
                db.commit()
                print(f"✅ Created user: {email} (password: {password})")
        else:
            print("\nUsage: python init_user.py <email> <password> [role]")
            print("Example: python init_user.py admin@dev.resolvify.tech admin123 admin")
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

