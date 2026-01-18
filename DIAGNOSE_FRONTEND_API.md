# Frontend API Connectivity Diagnosis

## Findings

1. **NEXT_PUBLIC_API_BASE_URL is empty** ✅ (This is correct - should use relative URLs)
2. **Database connection works** ✅ (Backend can connect to DB)
3. **Frontend error**: "Failed to find Server Action 'x'" ⚠️

## The Setup (from next.config.js)

- Next.js should rewrite `/api/:path*` → `http://backend:8000/api/:path*`
- Frontend uses relative URLs like `/api/v1/...` 
- Next.js dev server should proxy these to the backend container

## Issue: Check if DOCKER env var is set in frontend

The `next.config.js` checks for `DOCKER` or `IN_DOCKER` to determine `internalApiBase`.
If these aren't set, it might fall back to `localhost:8000` which won't work in Docker.

## Quick Fixes to Try

1. **Check DOCKER env var**:
   ```bash
   docker exec bot-dev-frontend env | grep DOCKER
   ```

2. **Restart frontend** (if env vars are missing, add them to docker-compose.dev.yml):
   ```bash
   docker-compose -f docker-compose.dev.yml restart frontend
   ```

3. **Test API endpoint from host**:
   ```bash
   curl -v https://dev.resolvify.tech/api/v1/health
   ```

4. **Check frontend logs for rewrite/proxy errors**:
   ```bash
   docker-compose -f docker-compose.dev.yml logs frontend --tail=100 | grep -i "rewrite\|proxy\|api\|error"
   ```

## Potential Root Cause

The `next.config.js` determines `internalApiBase` based on `isDocker` which checks:
- `IN_DOCKER === '1'` or `'true'`
- `DOCKER === '1'`

If these aren't set in the frontend container environment, it defaults to `http://localhost:8000`, which won't resolve to the backend container in Docker.

Check docker-compose.dev.yml - the frontend service should have `DOCKER=1` or `IN_DOCKER=1` in its environment section.
