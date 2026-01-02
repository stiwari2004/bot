# Verify Dev Environment is Working

## Step 1: Test Backend Health

```bash
# Test backend health endpoint
curl http://localhost:8001/health

# Should return JSON with status
```

## Step 2: Check Frontend Logs

```bash
# Check if frontend started successfully
docker-compose -f docker-compose.dev.yml -p bot-dev logs frontend | tail -30

# Look for "Ready" or "Local:" message indicating Next.js is running
```

## Step 3: Check Worker Logs

```bash
# Check if worker started successfully
docker-compose -f docker-compose.dev.yml -p bot-dev logs worker | tail -30

# Look for worker initialization messages
```

## Step 4: Test Frontend Access

```bash
# Test frontend directly (should return HTML or redirect)
curl -I http://localhost:3005

# Or test via nginx (if configured)
curl -I https://dev.resolvify.tech
```

## Step 5: Verify Production is Still Running

```bash
# Check production services (should still be running)
docker-compose -f docker-compose.production.yml ps

# Test production health
curl http://localhost:8000/health
```

## Step 6: Summary Check

```bash
# All dev services should be healthy
docker-compose -f docker-compose.dev.yml -p bot-dev ps

# All production services should be healthy
docker-compose -f docker-compose.production.yml ps
```

