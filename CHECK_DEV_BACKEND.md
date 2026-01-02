# Check Dev Backend Status

## Step 1: Check Current Status

```bash
# Check if dev containers are running
docker-compose -f docker-compose.dev.yml -p bot-dev ps

# Check dev backend logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -50

# Check if backend is healthy
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend curl http://localhost:8000/health || echo "Backend not responding"
```

## Step 2: Check Backend Logs for Errors

```bash
# Get full backend startup logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | grep -i "error\|exception\|traceback" | tail -30
```

## Step 3: Test Backend Health Endpoint

```bash
# From host (port 8001)
curl http://localhost:8001/health

# From inside container (port 8000)
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend curl http://localhost:8000/health
```

## Step 4: Check Database Connection

```bash
# Check if postgres is accessible from backend
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:dev_password_change_me@postgres:5432/troubleshooting_ai_dev'); print('DB connection OK')" || echo "DB connection failed"
```

## Step 5: If Backend is Not Running, Start It

```bash
# Start dev backend
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend

# Wait for it to start
sleep 10

# Check logs again
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -30
```

## Step 6: If Backend Has Errors, Check Common Issues

```bash
# Check if the model import error is fixed
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | grep -i "deployment_approval\|metadata\|InvalidRequestError"

# Check if database exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -c "\l" | grep troubleshooting_ai_dev

# Check if backend can connect to postgres
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend ping -c 2 postgres
```

