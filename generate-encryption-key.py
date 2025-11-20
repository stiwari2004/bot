#!/usr/bin/env python3
"""
Generate a Fernet encryption key for credential encryption
Run this once and add the output to CREDENTIAL_ENCRYPTION_KEY in docker-compose.yml
"""
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print("Generated encryption key:")
print(key.decode())
print("\nAdd this to docker-compose.yml as:")
print(f"  - CREDENTIAL_ENCRYPTION_KEY={key.decode()}")





