# Fix Dev ContainerConfig Error

## Remove Corrupted Container and Start Fresh

```bash
# Step 1: Force remove the corrupted dev backend container
docker-compose -f docker-compose.dev.yml -p bot-dev stop backend
docker rm -f bot-dev-backend 8dd26804de43_bot-dev-backend 2>/dev/null || true

# Remove any orphaned dev backend containers
docker ps -a | grep -E "bot-dev.*backend|bot-dev-backend" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Step 2: Clean up any dangling images (optional)
docker image prune -f

# Step 3: Start dev backend fresh
docker-compose -f docker-compose.dev.yml -p bot-dev up -d backend

# Step 4: Check logs
sleep 10
docker-compose -f docker-compose.dev.yml -p bot-dev logs backend | tail -30

# Step 5: Check status
docker-compose -f docker-compose.dev.yml -p bot-dev ps backend
```

