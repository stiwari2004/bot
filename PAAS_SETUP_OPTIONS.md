# PaaS Setup Options - User Guide

## Overview

We've implemented a **hybrid approach** to PaaS configuration that gives users flexibility based on their technical comfort level:

1. **Interactive CLI Script** (Quick & Easy) ⭐
2. **First-Run Setup UI** (Coming Soon - For Non-Technical Users)
3. **Manual Configuration** (For Advanced Users)

---

## Option 1: Interactive CLI Setup Script ⭐ **Recommended**

### What It Does

The setup script (`setup-paas.sh` or `setup-paas.ps1`) provides an interactive, guided experience:

- ✅ **Asks questions** about your configuration
- ✅ **Auto-generates secure keys** (SECRET_KEY, CREDENTIAL_ENCRYPTION_KEY)
- ✅ **Creates complete `.env` file** with sensible defaults
- ✅ **Backs up existing `.env`** if present
- ✅ **Validates inputs** and provides helpful defaults

### Usage

**Linux/Mac:**
```bash
./scripts/setup-paas.sh
```

**Windows:**
```powershell
.\scripts\setup-paas.ps1
```

### What You'll Be Asked

1. **Database Configuration**
   - Database URL (defaults to local Docker setup)

2. **Security**
   - Keys are auto-generated (no input needed)

3. **Environment**
   - Environment type (development/staging/production)
   - DEBUG mode (y/N)

4. **LLM Configuration**
   - LLM Provider (llamacpp/openai/anthropic)
   - LLM Base URL
   - LLM Model

5. **Optional APIs**
   - Perplexity API Key (optional)

6. **Frontend/Backend URLs**
   - For CORS configuration

### After Running

1. Review the generated `.env` file: `cat backend/.env` (or `Get-Content backend\.env` on Windows)
2. Adjust any values if needed
3. Start deployment: `docker-compose -f docker-compose.optimized.yml up -d`

---

## Option 2: First-Run Setup UI (Future Enhancement)

### Concept

When the application first starts, it checks configuration status via `/api/v1/setup/config/status`. If configuration is incomplete, a setup wizard UI appears.

### How It Works

1. **User deploys** the application (even without full config)
2. **Frontend loads** and calls `/api/v1/setup/config/status`
3. **If `setup_required: true`**, a setup wizard appears
4. **User fills out** the configuration form
5. **System generates** `.env` file (or updates environment variables)
6. **User restarts** the application

### Benefits

- ✅ **No command-line knowledge required**
- ✅ **Visual, guided experience**
- ✅ **Works for non-technical users**
- ✅ **Can validate configuration in real-time**

### Status

- ✅ Backend endpoint created (`/api/v1/setup/config/status`)
- ⏳ Frontend UI component (to be built)

---

## Option 3: Manual Configuration

### When to Use

- You prefer full control
- You're comfortable editing configuration files
- You have specific requirements not covered by the script

### Steps

1. Copy the example file:
   ```bash
   cd backend
   cp env.example .env
   ```

2. Edit `.env` with your favorite editor

3. Generate required keys:
   ```bash
   # SECRET_KEY
   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   
   # CREDENTIAL_ENCRYPTION_KEY
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

4. Fill in all required fields (see `env.example` for details)

---

## Configuration Status API

The backend provides an endpoint to check configuration status:

### Endpoint

```
GET /api/v1/setup/config/status
```

### Response

```json
{
  "is_configured": true,
  "missing_fields": [],
  "warnings": [],
  "database_status": "ready",
  "setup_required": false
}
```

### Use Cases

- **First-run UI**: Check if setup is needed
- **Health monitoring**: Verify configuration is valid
- **Troubleshooting**: Identify missing configuration

---

## Comparison

| Feature | CLI Script | Setup UI | Manual |
|---------|-----------|----------|--------|
| **Ease of Use** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Control** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Auto-Generate Keys** | ✅ | ✅ | ❌ |
| **Validation** | ✅ | ✅ | ❌ |
| **Non-Technical Friendly** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |

---

## Recommendation

**For Most Users:** Use the **Interactive CLI Script** (Option 1)
- Fastest setup
- Handles key generation automatically
- Provides sensible defaults
- Still allows customization

**For Non-Technical Users (Future):** Use the **First-Run Setup UI** (Option 2)
- Visual, guided experience
- No command-line required
- Real-time validation

**For Advanced Users:** Use **Manual Configuration** (Option 3)
- Full control
- Custom requirements
- Existing infrastructure integration

---

## Next Steps

1. ✅ **CLI Script** - Complete and ready to use
2. ✅ **Configuration Status API** - Complete
3. ⏳ **First-Run Setup UI** - To be built (part of admin UI work)
4. ✅ **Documentation** - Complete

---

## Questions?

- See `PAAS_DEPLOYMENT_GUIDE.md` for full deployment instructions
- Check `backend/env.example` for all available configuration options
- Review `scripts/setup-paas.sh` (or `.ps1`) to see what the script does








