# Quick Fix for ContainerConfig Error

## The Problem
The `ContainerConfig` error is a Docker Compose metadata corruption issue. It happens when Docker Compose tries to read container metadata that's corrupted or missing.

## Quick Solution (Since Your Containers Are Running)

Since your containers are already running, you can bypass the Docker Compose issue by using `docker exec` directly:

```bash
# Find your backend container name
docker ps | grep backend

# Run tests directly (replace CONTAINER_NAME with actual name)
docker exec -i CONTAINER_NAME pytest tests/ -v --no-cov --tb=line
```

## Updated Script

I've updated `run_tests.sh` to:
1. Detect if containers are running using `docker ps` (bypasses Compose)
2. Use `docker exec` directly instead of `docker-compose exec` (avoids ContainerConfig error)
3. Handle the error gracefully if it occurs

## To Fix the ContainerConfig Issue Properly (Tomorrow)

Run the fix script I created:

```bash
chmod +x fix_container_config_issue.sh
./fix_container_config_issue.sh
```

Or manually:

```bash
# Option 1: Restart Docker
sudo systemctl restart docker

# Option 2: Clean up and restart
docker-compose -f docker-compose.dev.yml down --remove-orphans
docker-compose -f docker-compose.dev.yml up -d

# Option 3: Remove specific containers
docker ps -a | grep bot | awk '{print $1}' | xargs docker rm -f
docker-compose -f docker-compose.dev.yml up -d
```

## For Now - Run Tests Directly

Since containers are running, you can run tests immediately:

```bash
# Find container name
CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)

# Run tests
docker exec -i $CONTAINER pytest tests/ -v --no-cov --tb=line > test_results.txt 2>&1

# View results
cat test_results.txt | tail -20
```

The updated `run_tests.sh` should now work even with the ContainerConfig error!
