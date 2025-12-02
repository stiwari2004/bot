#!/usr/bin/env python3
"""
Helper script to generate secure keys for the application.
Run this from the backend directory: python generate_keys.py
"""
import secrets
from cryptography.fernet import Fernet

print("=" * 60)
print("Generating Secure Keys for Troubleshooting AI Agent")
print("=" * 60)
print()

# Generate SECRET_KEY
secret_key = secrets.token_urlsafe(32)
print("1. SECRET_KEY (for JWT tokens):")
print(f"   {secret_key}")
print()

# Generate CREDENTIAL_ENCRYPTION_KEY
credential_key = Fernet.generate_key().decode()
print("2. CREDENTIAL_ENCRYPTION_KEY (for encrypting credentials):")
print(f"   {credential_key}")
print()

print("=" * 60)
print("Add these to your .env file or environment variables:")
print("=" * 60)
print()
print(f"SECRET_KEY={secret_key}")
print(f"CREDENTIAL_ENCRYPTION_KEY={credential_key}")
print()
print("=" * 60)
print("⚠️  IMPORTANT: Keep these keys secure and never commit them to git!")
print("=" * 60)




