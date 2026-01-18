# Tomorrow: Connectivity Investigation

## Issue
User reports connectivity problem (not password) - site is up but not connecting properly.

## What to Check

### 1. Frontend to Backend Connectivity
```bash
# Check if frontend can reach backend
docker exec bot-dev-frontend curl -v http://backend:8000/health

# Check frontend environment variables
docker exec bot-dev-frontend env | grep -i api
```

### 2. Backend to Database Connectivity
```bash
# Test database connection from backend
docker exec bot-dev-backend python -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text('SELECT 1'))
print('DB OK:', result.fetchone())
db.close()
"
```

### 3. Network Connectivity
```bash
# Check if containers can see each other
docker exec bot-dev-backend ping -c 2 postgres
docker exec bot-dev-backend ping -c 2 redis
docker exec bot-dev-frontend ping -c 2 backend

# Check network configuration
docker network inspect bot_app-dev-network
```

### 4. Check Logs for Connection Errors
```bash
# Backend logs
docker-compose -f docker-compose.dev.yml logs backend --tail=100 | grep -i "error\|connection\|timeout\|refused"

# Frontend logs
docker-compose -f docker-compose.dev.yml logs frontend --tail=100 | grep -i "error\|connection\|timeout\|refused"
```

### 5. Verify Environment Variables
```bash
# Check backend DATABASE_URL
docker exec bot-dev-backend env | grep DATABASE_URL

# Check frontend API URL
docker exec bot-dev-frontend env | grep -i api
```

## Notes
- SQL queries are executing (seen in logs), so database connection seems to work
- But user reports connectivity issues - may be frontend-to-backend or some other network path
- Need to trace the full request path from browser → frontend → backend → database

Good night! 🌙
