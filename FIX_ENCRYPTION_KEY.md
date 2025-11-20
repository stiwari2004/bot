# Fix Encryption Key Issue

## Problem
The credential encryption key was not set, causing a new key to be generated on each backend restart. This makes existing encrypted credentials unreadable.

## Solution

### Step 1: Generate a Fixed Encryption Key

Run this command to generate a proper Fernet encryption key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Or use the script:
```powershell
.\get-encryption-key.ps1
```

### Step 2: Update docker-compose.yml

Copy the generated key and update `docker-compose.yml`:

```yaml
environment:
  - CREDENTIAL_ENCRYPTION_KEY=<paste-your-generated-key-here>
```

### Step 3: Restart Backend

```powershell
docker-compose restart backend
```

### Step 4: Recreate Your Azure Credential

Since the old credential was encrypted with a different key, you need to recreate it:

1. Go to Settings → Infrastructure Connections
2. Delete the old credential (or create a new one)
3. Click "Add Credential"
4. Select type "Azure"
5. Enter:
   - Tenant ID
   - Client ID
   - Client Secret
   - Subscription ID (optional)
6. Save the credential
7. Update your infrastructure connection to use the new credential

### Step 5: Test Again

Click "Test" on your infrastructure connection - it should work now!

## Important Notes

- **DO NOT** change the encryption key after creating credentials, or you'll need to recreate them all
- For production, use a secure key management system (Azure Key Vault, AWS KMS, HashiCorp Vault)
- Keep the encryption key secure and backed up



