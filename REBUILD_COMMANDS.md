# Docker Rebuild Commands

## Important: Start Docker Desktop First!
Before running any Docker commands, make sure Docker Desktop is running:
1. Open Docker Desktop from Applications
2. Wait until it shows "Docker Desktop is running"

## Commands to Rebuild Frontend

### Option 1: Rebuild and restart frontend (recommended)
```bash
docker-compose up -d --build frontend
```

### Option 2: Stop, rebuild, then start separately
```bash
docker-compose stop frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### Option 3: Rebuild all services
```bash
docker-compose up -d --build
```

## Check Logs After Rebuilding

```bash
# Frontend logs
docker-compose logs -f frontend

# Backend logs (to check 500 errors)
docker-compose logs backend | tail -50

# All services
docker-compose logs | tail -100
```

## If System Keeps Crashing

The system crashes are likely due to memory issues (6GB RAM with Docker + LLM server).

**Quick Fix - Stop unnecessary services:**
```bash
# Stop worker (not critical for testing)
docker-compose stop worker

# Stop Redis if not using it
docker-compose stop redis
```

**Check memory usage:**
```bash
docker stats
```

**Use optimized docker-compose (if available):**
```bash
docker-compose -f docker-compose.optimized.yml up -d --build
```




