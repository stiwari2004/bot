#!/usr/bin/env python3
"""Simple key generator - outputs to console"""
import secrets
from cryptography.fernet import Fernet

secret_key = secrets.token_urlsafe(32)
credential_key = Fernet.generate_key().decode()

print("\n" + "="*70)
print("SECURE KEYS GENERATED - Copy these to your .env file:")
print("="*70)
print(f"\nSECRET_KEY={secret_key}")
print(f"\nCREDENTIAL_ENCRYPTION_KEY={credential_key}")
print("\n" + "="*70)
print("\n⚠️  Keep these keys secure! Never commit them to git.\n")




