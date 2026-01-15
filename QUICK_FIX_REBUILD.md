# Quick Fix: Rebuild Backend Container

The backend container is still running old code. Since the backend code is built into the Docker image (not volume-mounted), you need to rebuild the container.

## Option 1: Rebuild and Restart (Recommended)

```bash
# Rebuild the backend image
docker-compose -f docker-compose.dev.yml build backend

# Restart the container
docker-compose -f docker-compose.dev.yml up -d backend
```

## Option 2: Full Rebuild (If Option 1 doesn't work)

```bash
# Stop the container
docker-compose -f docker-compose.dev.yml stop backend

# Rebuild without cache (slower but ensures clean build)
docker-compose -f docker-compose.dev.yml build --no-cache backend

# Start the container
docker-compose -f docker-compose.dev.yml up -d backend
```

## Option 3: Quick Restart (If hot reload is enabled)

If the container has hot reload enabled and the code is volume-mounted, just restart:

```bash
docker-compose -f docker-compose.dev.yml restart backend
```

## Verify the Fix

After rebuilding, check the logs to ensure the error is gone:

```bash
docker-compose -f docker-compose.dev.yml logs --tail=50 backend
```

You should no longer see the `AttributeError: 'MutableHeaders' object has no attribute 'pop'` error.

## Check the File in Container

To verify the fix is in the container:

```bash
docker exec bot-dev-backend cat /app/app/core/security_middleware.py | grep -A 2 "Remove server"
```

Should show:
```python
# Remove server header (security through obscurity)
if "server" in response.headers:
    del response.headers["server"]
```

NOT:
```python
response.headers.pop("server", None)  # This is the old broken code
```
