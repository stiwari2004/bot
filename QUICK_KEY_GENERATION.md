# Quick Key Generation Guide

## Problem
PowerShell isn't showing Python output, and `pip` isn't in PATH.

## Solution: Use `python -m pip`

Run these commands in PowerShell from the `backend` directory:

```powershell
# Navigate to backend
cd backend

# Install cryptography using python -m pip
python -m pip install cryptography

# Generate keys
python generate_keys_simple.py
```

## Alternative: If Python isn't working either

If `python` command doesn't work, try:

```powershell
# Try python3
python3 -m pip install cryptography
python3 generate_keys_simple.py

# Or try py launcher
py -m pip install cryptography
py generate_keys_simple.py
```

## Manual Generation (if all else fails)

If you can't run Python scripts, you can use online tools or generate them manually:

### SECRET_KEY
- Use any secure random string generator
- Must be at least 32 characters
- Example format: `aBc123XyZ...` (43 characters recommended)

### CREDENTIAL_ENCRYPTION_KEY  
- Must be a valid Fernet key (base64-encoded)
- Format: 44 characters, base64
- You can use: https://8gwifi.org/fernetkeygen.jsp (online generator)
- Or install cryptography in a different environment and generate

## Using Docker (if available)

If you have Docker running:

```powershell
docker-compose exec backend python generate_keys_simple.py
```

This will use the Python environment inside the Docker container.




