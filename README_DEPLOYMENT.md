# Deployment Documentation

## Quick Links

- **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)** - Complete deployment architecture and plan
- **[DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)** - Step-by-step deployment guide
- **[PAAS_DEPLOYMENT_GUIDE.md](PAAS_DEPLOYMENT_GUIDE.md)** - Alternative PaaS deployment options

## Files Created for Deployment

### Scripts
- `scripts/backup-demo-data.sh` - Backup demo data from local development
- `scripts/restore-demo-data.sh` - Restore demo data on server
- `scripts/backup-production.sh` - Automated daily backups
- `scripts/deploy-production.sh` - Deploy to production instance
- `scripts/deploy-dev.sh` - Deploy to development instance
- `scripts/setup-server.sh` - Initial server setup (Docker, Nginx, etc.)

### Docker Compose Files
- `docker-compose.production.yml` - Production configuration (demo.yourdomain.com)
- `docker-compose.dev.yml` - Development configuration (dev.yourdomain.com)

### Nginx Configurations
- `nginx/troubleshooting-ai-demo.conf` - Main production instance
- `nginx/troubleshooting-ai-admin.conf` - Admin redirect
- `nginx/troubleshooting-ai-dev.conf` - Development instance
- `nginx/troubleshooting-ai-backend.conf` - Optional backend API access

## DNS Setup

You have configured the following A records:
- `demo.yourdomain.com` → Production instance
- `dev.yourdomain.com` → Development instance
- `admin.yourdomain.com` → Redirects to demo.yourdomain.com/super-admin
- `backend.yourdomain.com` → Optional direct API access (IP restricted)

## Deployment Workflow

### 1. Local Development (Windows)
- Use `docker-compose.yml` for local development
- Demo data stays in local database
- Develop and test features locally

### 2. Backup Demo Data
```powershell
# On Windows
docker-compose exec postgres pg_dump -U postgres troubleshooting_ai > backups\demo_data_backup.sql
```

### 3. Deploy to Server
```bash
# On Ubuntu server
cd /opt/troubleshooting-ai-demo
./scripts/deploy-production.sh
```

### 4. Restore Demo Data
```bash
# On server
./scripts/restore-demo-data.sh backups/demo_data_backup.sql
```

## Environment Configuration

### Production (demo.yourdomain.com)
- `ENVIRONMENT=production`
- `DEBUG=false`
- `ALLOWED_HOSTS=["https://demo.yourdomain.com", "https://admin.yourdomain.com"]`

### Development (dev.yourdomain.com)
- `ENVIRONMENT=development`
- `DEBUG=true` (optional)
- `ALLOWED_HOSTS=["https://dev.yourdomain.com"]`

## Security Notes

1. **Change all default passwords** before going live
2. **Generate strong secrets** for SECRET_KEY and CREDENTIAL_ENCRYPTION_KEY
3. **Enable SSL** for all subdomains
4. **Restrict backend subdomain** with IP whitelist if exposing
5. **Configure firewall** to only allow ports 22, 80, 443
6. **Set up automated backups** for production database

## Maintenance

### Daily Backups
Set up cron job:
```bash
crontab -e
# Add: 0 2 * * * /opt/troubleshooting-ai-demo/scripts/backup-production.sh
```

### View Logs
```bash
docker compose -f docker-compose.production.yml logs -f
```

### Update Application
```bash
cd /opt/troubleshooting-ai-demo
git pull origin main
./scripts/deploy-production.sh
```

## Troubleshooting

See [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md) for troubleshooting section.

## Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Verify nginx: `sudo nginx -t`
3. Check SSL: `sudo certbot certificates`
4. Review deployment guide: [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)

