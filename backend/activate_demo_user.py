#!/usr/bin/env python3
"""Activate demo user"""
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Check current status
result = db.execute(text("SELECT id, email, tenant_id, role, is_active FROM users WHERE email = 'demo@example.com'"))
user = result.fetchone()

if user:
    print(f'Found demo user: {user[1]}')
    print(f'Current status - ID: {user[0]}, Tenant: {user[2]}, Role: {user[3]}, Active: {user[4]}')
    
    if not user[4]:  # is_active is False
        db.execute(text("UPDATE users SET is_active = true WHERE email = 'demo@example.com'"))
        db.commit()
        print('✅ Demo user activated successfully!')
        
        # Verify
        result = db.execute(text("SELECT is_active FROM users WHERE email = 'demo@example.com'"))
        updated = result.fetchone()
        print(f'Verified - Active: {updated[0]}')
    else:
        print('✅ Demo user is already active')
else:
    print('❌ Demo user not found!')

db.close()
