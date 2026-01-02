# Dev/Production Interaction Review

## ✅ GOOD - Properly Isolated

### 1. Database Names
- **Production**: `troubleshooting_ai`
- **Dev**: `troubleshooting_ai_dev`
- ✅ **ISOLATED** - Different databases

### 2. Container Names
- **Production**: Uses default names (bot_backend_1, etc.)
- **Dev**: Explicit names (bot-dev-backend, bot-dev-postgres, etc.)
- ✅ **ISOLATED** - Different container names

### 3. Networks
- **Production**: `bot_app-network` (external)
- **Dev**: `bot_app-dev-network` (bridge)
- ✅ **ISOLATED** - Different networks

### 4. Ports
- **Production**: Backend 8000, Frontend 3004
- **Dev**: Backend 8001, Frontend 3005
- ✅ **ISOLATED** - Different ports

### 5. Database Volumes
- **Production**: `postgres_data`, `redis_data`
- **Dev**: `postgres_dev_data`, `redis_dev_data`
- ✅ **ISOLATED** - Different volumes

---

## ⚠️ ISSUES - Shared Resources

### 1. **SHARED UPLOADS DIRECTORY** ⚠️ CRITICAL
**Location**: Both docker-compose files
```yaml
# Production
volumes:
  - ./uploads:/app/uploads

# Dev  
volumes:
  - ./uploads:/app/uploads
```
**Problem**: Both environments write to the same `./uploads` directory on the host
**Impact**: Files uploaded in dev could conflict with production files
**Fix Needed**: Use separate upload directories

### 2. **SHARED .env FILE** ⚠️ CRITICAL
**Location**: Both docker-compose files
```yaml
# Production
env_file:
  - ./backend/.env

# Dev
env_file:
  - ./backend/.env
```
**Problem**: Both environments use the same `.env` file
**Impact**: Environment variables could conflict (e.g., DATABASE_URL, SECRET_KEY)
**Fix Needed**: Dev should use `./backend/.env.dev` or override all env vars in docker-compose

### 3. **Hardcoded localhost URLs in Code** ⚠️ MEDIUM
**Locations**:
- `backend/app/core/config.py` (lines 38, 92-93): Default localhost URLs
- `backend/app/main.py` (line 212): CORS origins with localhost:8000
- `backend/worker/main.py` (line 15): Default localhost:8000
- `frontend-nextjs/src/lib/config.ts`: Default localhost:8000

**Problem**: Code has hardcoded defaults that might not respect environment variables
**Impact**: Could cause issues if env vars aren't set properly
**Status**: Most use env vars, but defaults are hardcoded

---

## 🔍 DETAILED FINDINGS

### Backend Configuration Issues

1. **CORS Origins** (`backend/app/main.py:212`)
   - Hardcoded: `["http://localhost:3000", "http://localhost:3001", "http://localhost:8000", "http://localhost:8001"]`
   - Should use `settings.ALLOWED_HOSTS` from config

2. **Default URLs** (`backend/app/core/config.py`)
   - `FRONTEND_BASE_URL`: Defaults to `http://localhost:3000`
   - `BACKEND_BASE_URL`: Defaults to `http://localhost:8000`
   - These are overridden in docker-compose, but defaults could cause issues

3. **Worker Backend URL** (`backend/worker/main.py:15`)
   - Defaults to `http://localhost:8000`
   - Dev worker should use `http://backend:8000` (which it does via env var)

### Frontend Configuration Issues

1. **API Base URL** (`frontend-nextjs/src/lib/config.ts`)
   - Defaults to `http://localhost:8000`
   - Should use `NEXT_PUBLIC_API_BASE_URL` env var (which is set in docker-compose)

2. **OAuth Callback URLs** (Multiple files)
   - Hardcoded `http://localhost:8000/oauth/callback` in several places
   - Should use environment variable or settings

---

## 🛠️ RECOMMENDED FIXES

### Priority 1: Critical Fixes

1. **Separate Upload Directories**
   ```yaml
   # Dev docker-compose.dev.yml
   volumes:
     - ./uploads-dev:/app/uploads
   ```

2. **Separate .env Files**
   ```yaml
   # Dev docker-compose.dev.yml
   env_file:
     - ./backend/.env.dev  # Create this file
   ```

### Priority 2: Code Improvements

1. **Remove Hardcoded localhost URLs**
   - Ensure all URLs come from environment variables
   - Remove hardcoded defaults where possible

2. **Use Settings for CORS**
   - Use `settings.ALLOWED_HOSTS` instead of hardcoded list in main.py

---

## 📋 CHECKLIST BEFORE BUILDING DEV

- [ ] Create separate `./uploads-dev` directory
- [ ] Update dev docker-compose to use `./uploads-dev`
- [ ] Create `./backend/.env.dev` file (or ensure all env vars are in docker-compose)
- [ ] Verify no hardcoded URLs will conflict
- [ ] Test that dev can start without affecting production

