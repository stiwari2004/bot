# Quick Fix for ContainerConfig Error

## Option 1: Use the Fix Script (Recommended)
```bash
chmod +x fix_container_config_issue.sh
./fix_container_config_issue.sh docker-compose.dev.yml
```

## Option 2: Manual Quick Fix
Run these commands in order on your Linux server:

```bash
# 1. Stop and remove all containers
docker-compose -f docker-compose.dev.yml down --remove-orphans

# 2. Force remove the problematic containers
docker rm -f c02b8fa79685_bot_redis_1 520cc12f4ccb_bot_postgres_1 bot-dev-postgres bot-dev-redis 2>/dev/null || true

# 3. Remove corrupted images
docker rmi -f pgvector/pgvector:pg15 redis:7.2-alpine 2>/dev/null || true

# 4. Clean up Docker
docker system prune -f

# 5. Restart Docker (if you have sudo)
sudo systemctl restart docker
sleep 5

# 6. Start services with --force-recreate (bypasses ContainerConfig check)
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# 7. Verify
docker-compose -f docker-compose.dev.yml ps
```

## Option 3: Nuclear Option (if above doesn't work)
```bash
# WARNING: This removes ALL unused Docker data
docker system prune -a --volumes
sudo systemctl restart docker
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

## Key Point
The `--force-recreate` flag bypasses Docker Compose's attempt to read the corrupted `ContainerConfig` metadata, forcing it to create fresh containers.
