# Dev Environment Setup Guide

This guide sets up a development workflow where:
1. **Local Development**: Code on your laptop
2. **Dev Server**: Test on `dev.resolvify.tech` 
3. **Production**: Approved changes sync to `resolvify.tech`

## Architecture

- **Local**: Your laptop (development)
- **Dev**: `dev.resolvify.tech` (testing/staging)
- **Production**: `resolvify.tech` (live)

## Step 1: Set Up Dev Environment on Server

### 1.1 Create Dev Docker Compose

The dev environment uses different ports to run alongside production:

```bash
cd /home/opsbot/bot

# Dev will use:
# - Frontend: port 3005 (production uses 3004)
# - Backend: port 8001 (production uses 8000)
# - Postgres: internal only (no host port)
# - Redis: internal only (no host port)
```

### 1.2 Create Dev Environment File

```bash
# Copy production env as template
cp backend/.env backend/.env.dev

# Edit dev-specific settings
nano backend/.env.dev
```

**Key differences for dev:**
- `ENVIRONMENT=development`
- `DEBUG=true` (optional, for verbose logging)
- Same API keys as production (or use test keys)

### 1.3 Start Dev Environment

```bash
cd /home/opsbot/bot

# Start dev environment
docker compose -f docker-compose.dev.yml up -d

# Check status
docker compose -f docker-compose.dev.yml ps

# View logs
docker compose -f docker-compose.dev.yml logs -f
```

## Step 2: Configure Nginx for Dev

Add nginx config for `dev.resolvify.tech`:

```bash
sudo nano /etc/nginx/sites-available/dev.resolvify.tech
```

**Content:**
```nginx
# Dev environment - dev.resolvify.tech
server {
    server_name dev.resolvify.tech;

    # Proxy API requests to backend
    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy health check to backend
    location /health {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy everything else to frontend
    location / {
        proxy_pass http://localhost:3005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/resolvify.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/resolvify.tech/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# HTTP to HTTPS redirect
server {
    if ($host = dev.resolvify.tech) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name dev.resolvify.tech;
    return 404;
}
```

Enable and reload:
```bash
sudo ln -sf /etc/nginx/sites-available/dev.resolvify.tech /etc/nginx/sites-enabled/dev.resolvify.tech
sudo nginx -t
sudo systemctl reload nginx
```

## Step 3: Create Dev Tenant and Users

```bash
# Create dev tenant
docker compose -f docker-compose.dev.yml exec backend python scripts/create_customer_tenant.py \
  --name "Dev Team" \
  --slug "dev-team" \
  --email "dev@resolvify.tech" \
  --password "DevPassword123!" \
  --full-name "Dev Team Admin"
```

## Step 4: Development Workflow

### 4.1 Local Development

1. **Code on your laptop** in the repo
2. **Test locally** (if you have local setup)
3. **Commit and push** to a `dev` branch:

```bash
# On your laptop
git checkout -b dev
git add .
git commit -m "Feature: new runbook feature"
git push origin dev
```

### 4.2 Deploy to Dev Server

```bash
# On dev server
cd /home/opsbot/bot

# Pull dev branch
git fetch origin
git checkout dev
git pull origin dev

# Rebuild and restart dev environment
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d

# Check logs
docker compose -f docker-compose.dev.yml logs -f backend
```

### 4.3 Test on Dev

- Access: `https://dev.resolvify.tech`
- Login with dev team credentials
- Test new features
- Create/approve runbooks

### 4.4 Promote to Production

Once tested and approved:

```bash
# On dev server
cd /home/opsbot/bot

# Merge dev to main
git checkout main
git merge dev
git push origin main

# Deploy to production
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

## Step 5: Export/Import Runbooks

### Export Runbooks from Dev

```bash
# Export approved runbooks from dev
docker compose -f docker-compose.dev.yml exec backend python scripts/export_runbooks.py \
  --tenant-id 1 \
  --status approved \
  --output /app/exports/runbooks-dev.json
```

### Import Runbooks to Production

```bash
# Import runbooks to production
docker compose -f docker-compose.production.yml exec backend python scripts/import_runbooks.py \
  --input /app/exports/runbooks-dev.json \
  --target-tenant-id 1
```

## Step 6: Team Access

### Create Team Members

```bash
# Create additional dev team users
docker compose -f docker-compose.dev.yml exec backend python scripts/create_customer_tenant.py \
  --name "Team Member Name" \
  --slug "team-member" \
  --email "teammember@resolvify.tech" \
  --password "TeamPassword123!"
```

### Access URLs

- **Dev**: `https://dev.resolvify.tech/c/dev-team`
- **Production**: `https://resolvify.tech` (after approval)

## Quick Reference

### Dev Environment Commands

```bash
# Start dev
docker compose -f docker-compose.dev.yml up -d

# Stop dev
docker compose -f docker-compose.dev.yml down

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Rebuild after code changes
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d

# Access dev database
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d troubleshooting_ai_dev
```

### Production Environment Commands

```bash
# Start production
docker compose -f docker-compose.production.yml up -d

# Deploy latest code
git pull origin main
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

## Troubleshooting

### Port Conflicts

If ports 8001 or 3005 are in use:
- Check: `sudo lsof -i :8001` or `sudo lsof -i :3005`
- Update `docker-compose.dev.yml` to use different ports
- Update nginx config accordingly

### Database Issues

Dev uses a separate database (`troubleshooting_ai_dev`). If you need to reset:
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

