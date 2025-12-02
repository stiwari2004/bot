# How to Generate Secure Keys

Since you're in PowerShell and the `cryptography` module might not be in your current Python environment, here are the options:

## Option 1: Use the Helper Script (Recommended)

I've created a helper script for you. Run this from the **backend** directory:

```powershell
cd backend
python generate_keys.py
```

This will generate both keys and display them with instructions.

## Option 2: Run from Backend Directory with Dependencies

If you have a virtual environment or the backend dependencies installed:

```powershell
cd backend
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print('CREDENTIAL_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

## Option 3: Install cryptography in Current Environment

If you want to generate keys from anywhere:

```powershell
pip install cryptography
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Option 4: Use Docker (if you have it running)

If your backend is running in Docker:

```powershell
docker-compose exec backend python generate_keys.py
```

## Quick Copy-Paste for .env File

Once you have the keys, add them to your `.env` file in the backend directory:

```bash
# Security Keys (REQUIRED)
SECRET_KEY=<your-generated-secret-key-here>
CREDENTIAL_ENCRYPTION_KEY=<your-generated-fernet-key-here>

# Database (REQUIRED - use strong password)
DATABASE_URL=postgresql://postgres:your_strong_password@localhost:5432/troubleshooting_ai

# Environment
ENVIRONMENT=development
```

## Notes

- **SECRET_KEY**: Must be at least 32 characters (the generated one is 43)
- **CREDENTIAL_ENCRYPTION_KEY**: Must be a valid Fernet key (base64-encoded, 44 characters)
- **Never commit these keys to git!**
- If you change `CREDENTIAL_ENCRYPTION_KEY`, existing encrypted credentials will need to be re-encrypted




