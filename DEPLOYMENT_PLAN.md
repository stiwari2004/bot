# Production Deployment Plan: Multi-Subdomain Setup

## DNS Configuration

You have set up the following A records:
- **demo.yourdomain.com** → Demo/Production instance (with demo data)
- **dev.yourdomain.com** → Development instance
- **admin.yourdomain.com** → Super Admin access (redirects to demo.yourdomain.com/super-admin)
- **backend.yourdomain.com** → Direct backend API access (optional, restricted)

## Architecture Overview

```
Internet
  ├── demo.yourdomain.com (Main app - Production with demo data)
  │   ├── / → Frontend (Next.js)
  │   ├── /api → Backend API (FastAPI)
  │   └── /super-admin → Super Admin UI
  │
  ├── dev.yourdomain.com (Development instance)
  │   ├── / → Frontend (Next.js)
  │   └── /api → Backend API (FastAPI)
  │
  ├── admin.yourdomain.com (Redirect to demo.yourdomain.com/super-admin)
  │
  └── backend.yourdomain.com (Optional - Direct API access, IP restricted)
      └── / → Backend API (FastAPI)
```

## Phase 1: Local Data Backup

### 1.1 Create Backup Script
**File**: `scripts/backup-demo-data.sh`

This script will:
- Export PostgreSQL database with all demo data
- Create timestamped backup file
- Verify backup integrity

### 1.2 Backup Process
Run on your local Windows machine:
```powershell
# Using Docker Compose
docker-compose exec postgres pg_dump -U postgres troubleshooting_ai > demo_data_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql
```

## Phase 2: Server Setup

### 2.1 Server Requirements
- Ubuntu 22.04 LTS
- Docker & Docker Compose installed
- Nginx installed
- Ports available: 3000, 8000, 5432, 6379 (or custom)
- SSL certificates (Let's Encrypt)

### 2.2 Directory Structure
```
/opt/
  ├── troubleshooting-ai-demo/  (Production instance)
  │   ├── docker-compose.production.yml
  │   ├── backend/
  │   ├── frontend-nextjs/
  │   └── backups/
  │
  └── troubleshooting-ai-dev/   (Development instance)
      ├── docker-compose.dev.yml
      ├── backend/
      └── frontend-nextjs/
```

## Phase 3: Production Configuration

### 3.1 Environment Files

**demo.yourdomain.com** (`/opt/troubleshooting-ai-demo/backend/.env`):
- `ENVIRONMENT=production`
- `ALLOWED_HOSTS=["https://demo.yourdomain.com", "https://admin.yourdomain.com"]`
- `NEXT_PUBLIC_API_BASE_URL=https://demo.yourdomain.com/api`

**dev.yourdomain.com** (`/opt/troubleshooting-ai-dev/backend/.env`):
- `ENVIRONMENT=development`
- `ALLOWED_HOSTS=["https://dev.yourdomain.com"]`
- `NEXT_PUBLIC_API_BASE_URL=https://dev.yourdomain.com/api`

### 3.2 Docker Compose Files

Create separate compose files:
- `docker-compose.production.yml` - For demo instance
- `docker-compose.dev.yml` - For dev instance

Both use:
- Isolated networks
- Separate volumes
- Production/development settings

## Phase 4: Nginx Configuration

### 4.1 Main Demo Instance
**File**: `/etc/nginx/sites-available/troubleshooting-ai-demo`

- Handles `demo.yourdomain.com`
- Proxies `/` → Frontend (port 3000)
- Proxies `/api` → Backend (port 8000)
- SSL with Let's Encrypt

### 4.2 Admin Redirect
**File**: `/etc/nginx/sites-available/troubleshooting-ai-admin`

- Handles `admin.yourdomain.com`
- Redirects to `https://demo.yourdomain.com/super-admin`
- SSL with Let's Encrypt

### 4.3 Dev Instance
**File**: `/etc/nginx/sites-available/troubleshooting-ai-dev`

- Handles `dev.yourdomain.com`
- Proxies `/` → Frontend (port 3001)
- Proxies `/api` → Backend (port 8001)
- SSL with Let's Encrypt

### 4.4 Backend API (Optional)
**File**: `/etc/nginx/sites-available/troubleshooting-ai-backend`

- Handles `backend.yourdomain.com`
- IP whitelist restriction
- Proxies `/` → Backend (port 8000)
- SSL with Let's Encrypt

## Phase 5: Data Transfer & Restoration

### 5.1 Transfer Backup
```bash
# From local machine
scp demo_data_backup.sql user@your-server:/opt/troubleshooting-ai-demo/
```

### 5.2 Restore Data
```bash
# On server, after starting postgres
cd /opt/troubleshooting-ai-demo
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U postgres troubleshooting_ai < demo_data_backup.sql
```

## Phase 6: Deployment Steps

### 6.1 Deploy Demo Instance
1. Clone repository to `/opt/troubleshooting-ai-demo`
2. Configure `.env` files
3. Build and start services
4. Restore demo data
5. Configure nginx
6. Set up SSL certificates

### 6.2 Deploy Dev Instance
1. Clone repository to `/opt/troubleshooting-ai-dev`
2. Configure `.env` files (development settings)
3. Build and start services
4. Configure nginx
5. Set up SSL certificates

## Phase 7: Development Workflow

### 7.1 Local Development
- Continue developing on Windows machine
- Use `docker-compose.yml` for local testing
- Demo data remains in local database

### 7.2 Git Workflow
- `main` branch → Auto-deploy to `demo.yourdomain.com`
- `dev` branch → Auto-deploy to `dev.yourdomain.com`
- Feature branches → Test locally, merge to dev, then main

### 7.3 Deployment Scripts
- `scripts/deploy-demo.sh` - Deploy to production
- `scripts/deploy-dev.sh` - Deploy to dev
- `scripts/backup-production.sh` - Automated backups

## Security Considerations

1. **Backend Subdomain**: If exposing `backend.yourdomain.com`:
   - IP whitelist in nginx
   - API key authentication
   - Rate limiting

2. **SSL Certificates**: All subdomains need SSL
   - Use Let's Encrypt wildcard cert OR
   - Individual certs for each subdomain

3. **Firewall**: Only expose ports 80, 443
   - All other ports (3000, 8000, 5432, 6379) internal only

## Monitoring & Maintenance

1. **Backups**: Daily automated backups
2. **Logs**: Centralized logging
3. **Health Checks**: Monitor service health
4. **Updates**: Rolling updates with zero downtime

## Next Steps

1. Create backup script
2. Create production docker-compose file
3. Create nginx configurations
4. Create deployment scripts
5. Test deployment process

