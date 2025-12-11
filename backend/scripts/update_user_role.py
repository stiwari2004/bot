#!/usr/bin/env python3
"""
Script to update a user's role
Usage: python scripts/update_user_role.py <email> <new_role>
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


async def update_user_role(email: str, new_role: str):
    """Update a user's role"""
    
    # Initialize database
    await init_db()
    
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User with email {email} not found")
            return False
        
        old_role = user.role
        user.role = new_role
        db.commit()
        db.refresh(user)
        
        print(f"✅ Updated user {email}")
        print(f"   Old role: {old_role}")
        print(f"   New role: {user.role}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating user role: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/update_user_role.py <email> <new_role>")
        print("Example: python scripts/update_user_role.py admin@example.com super_admin")
        sys.exit(1)
    
    email = sys.argv[1]
    new_role = sys.argv[2]
    
    # Validate role
    valid_roles = ["super_admin", "admin", "user", "viewer"]
    if new_role not in valid_roles:
        print(f"❌ Invalid role. Must be one of: {', '.join(valid_roles)}")
        sys.exit(1)
    
    asyncio.run(update_user_role(email, new_role))







