#!/usr/bin/env python3
"""
Test password verification with exact hash from database
"""
import sys
sys.path.insert(0, '/app')

from app.services.auth import verify_password, get_password_hash

# Exact hash from database
db_hash = "$pbkdf2-sha256$29000$CsE459xbC6HUulfqXSuFUA$gVwkjp1qIrtqCc7FsC/q0o5Gz6vLN1U6410483cgdAA"
test_password = "S@ndysango1982"

print(f"Testing password: {test_password[:3]}*** (length: {len(test_password)})")
print(f"Hash from DB: {db_hash[:50]}...")
print(f"Hash length: {len(db_hash)}")
print(f"Hash format: {db_hash.split('$')[0] if '$' in db_hash else 'unknown'}")

print("\n=== Testing verification ===")
try:
    result = verify_password(test_password, db_hash)
    print(f"✅ Verification result: {result}")
    if result:
        print("✅ Password is CORRECT!")
    else:
        print("❌ Password verification FAILED")
        
        # Try generating a new hash to see the format
        print("\n=== Generating new hash for comparison ===")
        new_hash = get_password_hash(test_password)
        print(f"New hash: {new_hash[:50]}...")
        print(f"New hash length: {len(new_hash)}")
        print(f"New hash format: {new_hash.split('$')[0] if '$' in new_hash else 'unknown'}")
        
        # Check if formats match
        db_format = db_hash.split('$')[0] if '$' in db_hash else ''
        new_format = new_hash.split('$')[0] if '$' in new_hash else ''
        print(f"\nFormat comparison:")
        print(f"  DB hash format: {db_format}")
        print(f"  New hash format: {new_format}")
        print(f"  Formats match: {db_format == new_format}")
        
except Exception as e:
    print(f"❌ Exception during verification: {e}")
    import traceback
    traceback.print_exc()
