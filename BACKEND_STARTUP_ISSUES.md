# Backend Startup Issues - Diagnosis & Fix

## 🔍 Problem Identified

The backend is **stuck/failing to start** because:

1. **Missing Python Dependencies**: `ModuleNotFoundError: No module named 'pydantic'`
2. This means the backend can't even import its modules, so it crashes immediately

## 🚨 Root Cause

The Python environment doesn't have the required packages installed. The backend needs:
- `pydantic` (and many other dependencies)
- All packages from `backend/requirements.txt`

## ✅ Solutions

### Option 1: Install Dependencies (Recommended)

```bash
cd backend

# If using virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows PowerShell
# OR
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Use Docker (Easier)

```bash
# From project root
docker-compose up backend -d

# Check logs
docker-compose logs -f backend
```

### Option 3: Check if Backend is Running

```bash
# Windows PowerShell
netstat -an | findstr :8000

# If nothing shows, backend isn't running
# If something shows, backend might be stuck
```

## 🔧 Common Startup Blocking Issues

Based on `backend/app/main.py`, the backend can get stuck at:

### 1. Database Connection (Line 50: `await init_db()`)
- **Symptom**: Backend hangs during startup
- **Fix**: Check `DATABASE_URL` in `.env` file
- **Test**: Run `python backend/check_backend_status.py`

### 2. Embedding Model Preloading (Lines 69-90)
- **Symptom**: Backend takes 2-3 minutes to start
- **Fix**: Set `PRELOAD_EMBEDDING_MODEL=false` in `.env`
- **Note**: Model will load on first use (lazy loading)

### 3. Ticketing Poller Service (Lines 92-102)
- **Symptom**: Backend hangs during startup
- **Fix**: Set `ENABLE_TICKETING_POLLER=false` in `.env`
- **Note**: This disables background ticket polling

### 4. WebSocket Cleanup Task (Lines 54-61)
- **Symptom**: Usually not blocking, but can cause issues
- **Fix**: Usually auto-handles errors gracefully

## 🛠️ Quick Fix Commands

### Disable Blocking Services (Fastest Fix)

Create or update `backend/.env`:

```env
# Disable embedding model preloading (saves 2-3 minutes)
PRELOAD_EMBEDDING_MODEL=false

# Disable ticketing poller (if causing issues)
ENABLE_TICKETING_POLLER=false
```

### Check Backend Status

```bash
cd backend
python check_backend_status.py
```

This will show you exactly where it's getting stuck.

## 📋 Startup Sequence (from main.py)

1. ✅ Setup logging
2. ✅ Initialize rate limiting (if enabled)
3. ⚠️ **Database initialization** (`await init_db()`) - **CAN BLOCK**
4. ⚠️ **WebSocket cleanup task** - Usually OK
5. ⚠️ **Embedding model preloading** - **CAN BLOCK (2-3 min)**
6. ⚠️ **Ticketing poller service** - **CAN BLOCK**
7. ✅ Start FastAPI app

## 🎯 Recommended Startup Configuration

For development, use this `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Disable blocking services for faster startup
PRELOAD_EMBEDDING_MODEL=false
ENABLE_TICKETING_POLLER=false

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🔍 Debugging Steps

1. **Check if backend process exists**:
   ```bash
   # Windows
   tasklist | findstr python
   
   # Mac/Linux
   ps aux | grep uvicorn
   ```

2. **Check backend logs**:
   - If running with `uvicorn`, logs go to stdout
   - If running with Docker: `docker-compose logs backend`
   - Check `backend/logs/audit.log` for application logs

3. **Test database connection**:
   ```bash
   cd backend
   python -c "from app.core.database import engine; from sqlalchemy import text; engine.connect().execute(text('SELECT 1'))"
   ```

4. **Test configuration loading**:
   ```bash
   cd backend
   python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
   ```

## 🚀 Start Backend (After Fixing Dependencies)

```bash
cd backend

# Activate virtual environment (if using one)
.\venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Mac/Linux

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📝 Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Check database connection**: Ensure PostgreSQL is running
3. **Disable blocking services**: Add to `.env` if needed
4. **Start backend**: `uvicorn app.main:app --reload`
5. **Test**: `curl http://localhost:8000/health`

---

**Current Status**: Backend cannot start due to missing Python dependencies.







