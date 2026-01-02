# Start Dev Services and Verify

## Step 1: Verify Migrations Are Complete

```bash
# Check if runbooks table has environment column
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks" | grep -E "environment|promoted_from"

# Check if deployment_approvals table exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "\d deployment_approvals"
```

## Step 2: Start Frontend and Worker

```bash
# Start frontend and worker
docker-compose -f docker-compose.dev.yml -p bot-dev up -d frontend worker

# Wait a few seconds for services to start
sleep 10
```

## Step 3: Check All Services Status

```bash
# Check all dev services
docker-compose -f docker-compose.dev.yml -p bot-dev ps

# Check frontend logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs frontend | tail -20

# Check worker logs
docker-compose -f docker-compose.dev.yml -p bot-dev logs worker | tail -20
```

## Step 4: Test Dev Environment

```bash
# Test backend health
curl http://localhost:8001/health

# Test frontend (should be accessible via nginx at https://dev.resolvify.tech)
# Or check if frontend container is responding
curl http://localhost:3005
```

## Step 5: Verify Isolation from Production

```bash
# Check production is still running
docker-compose -f docker-compose.production.yml ps

# Verify ports are different
netstat -tuln | grep -E ":(8000|8001|3004|3005)" || ss -tuln | grep -E ":(8000|8001|3004|3005)"
```

