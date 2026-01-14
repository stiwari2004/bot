#!/usr/bin/env python3
"""Script to create a user"""
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_password_hash
from sqlalchemy import func

if len(sys.argv) < 3:
    print("Usage: python create_user.py <email> <password> [tenant_id] [role]")
    print("Example: python create_user.py admin@dev.resolvify.tech admin123 1 admin")
    sys.exit(1)

email = sys.argv[1]
password = sys.argv[2]
tenant_id = int(sys.argv[3]) if len(sys.argv) > 3 else 1
role = sys.argv[4] if len(sys.argv) > 4 else "admin"

db = SessionLocal()
try:
    # Check if user exists
    existing = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    if existing:
        print(f"User {email} already exists!")
        print(f"  ID: {existing.id}")
        print(f"  Role: {existing.role}")
        print(f"  Active: {existing.is_active}")
        print(f"\nTo reset password, use: python check_user.py {email} <new_password>")
        sys.exit(1)
    
    # Check tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        print(f"Tenant ID {tenant_id} not found!")
        print("Available tenants:")
        tenants = db.query(Tenant).all()
        for t in tenants:
            print(f"  ID: {t.id}, Name: {t.name}")
        sys.exit(1)
    
    # Create user
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=get_password_hash(password),
        full_name=email.split("@")[0].title(),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print(f"✅ Created user:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Role: {role}")
    print(f"   Tenant: {tenant.name} (ID: {tenant.id})")
    print(f"   User ID: {user.id}")
    
finally:
    db.close()

