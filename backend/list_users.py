#!/usr/bin/env python3
"""Script to list all users"""
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from sqlalchemy import func

db = SessionLocal()
try:
    print("=" * 60)
    print("All Users:")
    print("=" * 60)
    users = db.query(User).all()
    if not users:
        print("No users found in database")
    else:
        for user in users:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            tenant_name = tenant.name if tenant else "Unknown"
            print(f"ID: {user.id}, Email: {user.email}, Role: {user.role}, Tenant: {tenant_name}, Active: {user.is_active}")
    
    print("\n" + "=" * 60)
    print("All Tenants:")
    print("=" * 60)
    tenants = db.query(Tenant).all()
    for tenant in tenants:
        print(f"ID: {tenant.id}, Name: {tenant.name}, is_msp: {tenant.is_msp}, parent_tenant_id: {tenant.parent_tenant_id}")
    
finally:
    db.close()

