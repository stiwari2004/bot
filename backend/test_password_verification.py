#!/usr/bin/env python3
"""
Test password verification directly
"""
import sys
sys.path.insert(0, '/app')

from app.services.auth import verify_password, get_password_hash
from sqlalchemy import create_engine, text
from app.core.config import settings

def test_password(email: str, password: str):
    """Test password verification"""
    print(f"Testing password for: {email}")
    print(f"Password provided: {password[:3]}*** (length: {len(password)})")
    
    # Get hash from database
    db_url = settings.DATABASE_URL
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT password_hash FROM super_admins WHERE email = :email'),
            {'email': email}
        )
        row = result.fetchone()
        if not row:
            print(f"❌ No super admin found with email: {email}")
            return False
        
        db_hash = row[0]
        print(f"Hash from DB: {db_hash[:50]}... (length: {len(db_hash)})")
        print(f"Hash scheme: {db_hash.split('$')[0] if '$' in db_hash else 'unknown'}")
        
        # Test verification
        print("\nTesting password verification...")
        try:
            result = verify_password(password, db_hash)
            print(f"✅ Verification result: {result}")
            if result:
                print("✅ Password is CORRECT")
            else:
                print("❌ Password is INCORRECT")
                
                # Generate a new hash with the provided password to compare
                new_hash = get_password_hash(password)
                print(f"\nNew hash for provided password: {new_hash[:50]}...")
                print(f"DB hash:                      {db_hash[:50]}...")
                print(f"Hashes match: {new_hash == db_hash}")
                
        except Exception as e:
            print(f"❌ Exception during verification: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return result

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@dev.resolvify.tech"
    password = sys.argv[2] if len(sys.argv) > 2 else "S@ndysango1982"
    
    success = test_password(email, password)
    sys.exit(0 if success else 1)
