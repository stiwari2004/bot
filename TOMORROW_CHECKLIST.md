# Tomorrow Morning Checklist

## Container Issues to Fix

### 1. Stale Container State
- **Problem**: Postgres and Redis containers showing "Exit 0" (stopped)
- **Impact**: Backend may not be able to connect to database/redis
- **Fix Steps**:
  ```bash
  # Clean up stale containers
  docker-compose -f docker-compose.dev.yml down --remove-orphans
  
  # Restart Docker daemon (if ContainerConfig errors persist)
  sudo systemctl restart docker
  
  # Start services fresh
  docker-compose -f docker-compose.dev.yml up -d
  
  # Verify all containers are running
  docker-compose -f docker-compose.dev.yml ps
  ```

### 2. Admin Portal Authentication Issue
- **Problem**: `admin.resolvify.tech` not authenticating (dev.resolvify.tech works)
- **Check**:
  1. Verify production backend is running:
     ```bash
     docker-compose -f docker-compose.production.yml ps
     ```
  2. Check production backend logs:
     ```bash
     docker-compose -f docker-compose.production.yml logs backend --tail=100
     ```
  3. Verify database connection:
     ```bash
     docker-compose -f docker-compose.production.yml exec backend python -c "from app.core.database import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('DB OK')"
     ```
  4. Check if super admin exists:
     ```bash
     docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, is_active FROM super_admins;"
     ```
  5. Check frontend can reach backend:
     - Verify `BACKEND_BASE_URL` in production frontend config
     - Check CORS settings in production backend
     - Verify network connectivity between frontend and backend containers

### 3. Test Suite
- Run tests once containers are fixed:
  ```bash
  ./run_tests.sh
  ```

## Quick Diagnostic Commands

```bash
# Check all container statuses
docker ps -a | grep bot

# Check production backend health
curl https://admin.resolvify.tech/api/v1/health

# Check dev backend health  
curl https://dev.resolvify.tech/api/v1/health

# Check production backend logs for auth errors
docker-compose -f docker-compose.production.yml logs backend | grep -i "auth\|login\|401\|403"

# Check network connectivity
docker network ls
docker network inspect bot_app-network
```

## Priority Order
1. ✅ Fix stale containers (postgres/redis)
2. ✅ Fix admin.resolvify.tech authentication
3. ✅ Run test suite
4. ✅ Fix remaining ContainerConfig issues (if needed)

Good night! 🌙
