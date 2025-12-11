# Deployment Quick Start Guide

## Overview

This guide walks you through deploying the application to your Ubuntu server with the following subdomains:
- **demo.yourdomain.com** - Production instance with demo data
- **dev.yourdomain.com** - Development instance
- **admin.yourdomain.com** - Redirects to demo.yourdomain.com/super-admin
- **backend.yourdomain.com** - Optional direct API access (IP restricted)

## Prerequisites

- Ubuntu 22.04 LTS server
- SSH access to server
- DNS A records configured (demo, dev, admin, backend → your server IP)
- Domain name configured

## Step-by-Step Deployment

### Phase 1: Local Backup (Windows Machine)

1. **Backup demo data from local database:**
   ```powershell
   # Navigate to project directory
   cd C:\Users\Admin\Documents\bot
   
   # Create backup (using PowerShell)
   docker-compose exec postgres pg_dump -U postgres troubleshooting_ai > backups\demo_data_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql
   ```

2. **Verify backup file was created:**
   ```powershell
   ls backups\demo_data_backup_*.sql
   ```

### Phase 2: Server Initial Setup (Ubuntu Server)

1. **SSH into your server:**
   ```bash
   ssh user@your-server-ip
   ```

2. **Run initial setup script:**
   ```bash
   # Clone repository first (or upload files)
   git clone <your-repo-url> /opt/troubleshooting-ai-demo
   cd /opt/troubleshooting-ai-demo
   
   # Make scripts executable
   chmod +x scripts/*.sh
   
   # Run server setup (installs Docker, Nginx, etc.)
   ./scripts/setup-server.sh
   ```

3. **Log out and back in** (for Docker group changes)

### Phase 3: Configure Production Environment

1. **Create backend environment file:**
   ```bash
   cd /opt/troubleshooting-ai-demo/backend
   cp env.example .env
   nano .env  # Edit with your settings
   ```

2. **Required environment variables:**
   ```bash
   ENVIRONMENT=production
   DEBUG=false
   DATABASE_URL=postgresql://postgres:YOUR_STRONG_PASSWORD@postgres:5432/troubleshooting_ai
   SECRET_KEY=<generate-with-python>
   CREDENTIAL_ENCRYPTION_KEY=<generate-with-python>
   ALLOWED_HOSTS=["https://demo.yourdomain.com", "https://admin.yourdomain.com"]
   GEMINI_API_KEY=your_key_here
   PERPLEXITY_API_KEY=your_key_here
   ```

3. **Generate secrets:**
   ```bash
   # SECRET_KEY
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   
   # CREDENTIAL_ENCRYPTION_KEY
   python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

4. **Update docker-compose.production.yml:**
   ```bash
   # Set POSTGRES_PASSWORD in .env or docker-compose file
   nano docker-compose.production.yml
   ```

5. **Create frontend environment file:**
   ```bash
   cd /opt/troubleshooting-ai-demo/frontend-nextjs
   echo "NEXT_PUBLIC_API_BASE_URL=https://demo.yourdomain.com/api" > .env.production
   ```

### Phase 4: Transfer and Restore Demo Data

1. **Transfer backup file to server:**
   ```powershell
   # From Windows machine
   scp backups\demo_data_backup_*.sql user@your-server:/opt/troubleshooting-ai-demo/
   ```

2. **Start PostgreSQL container:**
   ```bash
   # On server
   cd /opt/troubleshooting-ai-demo
   docker compose -f docker-compose.production.yml up -d postgres
   
   # Wait for it to be ready
   sleep 10
   ```

3. **Restore demo data:**
   ```bash
   ./scripts/restore-demo-data.sh backups/demo_data_backup_*.sql
   ```

### Phase 5: Configure Nginx

1. **Copy nginx configurations:**
   ```bash
   sudo cp nginx/troubleshooting-ai-demo.conf /etc/nginx/sites-available/
   sudo cp nginx/troubleshooting-ai-admin.conf /etc/nginx/sites-available/
   sudo cp nginx/troubleshooting-ai-dev.conf /etc/nginx/sites-available/
   sudo cp nginx/troubleshooting-ai-backend.conf /etc/nginx/sites-available/
   ```

2. **Update domain names in configs:**
   ```bash
   # Replace 'yourdomain.com' with your actual domain
   sudo sed -i 's/yourdomain.com/your-actual-domain.com/g' /etc/nginx/sites-available/troubleshooting-ai-*.conf
   ```

3. **Enable sites:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/troubleshooting-ai-demo /etc/nginx/sites-enabled/
   sudo ln -s /etc/nginx/sites-available/troubleshooting-ai-admin /etc/nginx/sites-enabled/
   # Enable dev and backend if needed
   ```

4. **Test nginx configuration:**
   ```bash
   sudo nginx -t
   ```

5. **Reload nginx:**
   ```bash
   sudo systemctl reload nginx
   ```

### Phase 6: Set Up SSL Certificates

1. **Get SSL certificates for each subdomain:**
   ```bash
   # Demo instance
   sudo certbot --nginx -d demo.yourdomain.com
   
   # Admin redirect
   sudo certbot --nginx -d admin.yourdomain.com
   
   # Dev instance (if deploying)
   sudo certbot --nginx -d dev.yourdomain.com
   
   # Backend (if exposing)
   sudo certbot --nginx -d backend.yourdomain.com
   ```

2. **Verify certificates:**
   ```bash
   sudo certbot certificates
   ```

### Phase 7: Deploy Application

1. **Build and start services:**
   ```bash
   cd /opt/troubleshooting-ai-demo
   docker compose -f docker-compose.production.yml build
   docker compose -f docker-compose.production.yml up -d
   ```

2. **Check service status:**
   ```bash
   docker compose -f docker-compose.production.yml ps
   docker compose -f docker-compose.production.yml logs -f
   ```

3. **Verify deployment:**
   ```bash
   # Check backend health
   curl http://localhost:8000/health
   
   # Check frontend
   curl http://localhost:3000
   ```

### Phase 8: Verify Everything Works

1. **Test URLs:**
   - https://demo.yourdomain.com - Should show login page
   - https://admin.yourdomain.com - Should redirect to /super-admin
   - https://demo.yourdomain.com/api/docs - Should show API documentation

2. **Test login:**
   - Email: `demo@example.com`
   - Password: `demo123`

3. **Verify demo data:**
   - Check tickets are visible
   - Check runbooks are present
   - Check all features work

## Development Workflow

### Local Development (Windows)
- Continue using `docker-compose.yml`
- Develop features locally
- Test with demo data

### Deploy to Production
```bash
# On server
cd /opt/troubleshooting-ai-demo
./scripts/deploy-production.sh
```

### Deploy to Dev Instance
```bash
# On server
cd /opt/troubleshooting-ai-dev
./scripts/deploy-dev.sh  # (create this similar to production)
```

## Maintenance

### Daily Backups
```bash
# Set up cron job for automated backups
crontab -e
# Add: 0 2 * * * /opt/troubleshooting-ai-demo/scripts/backup-production.sh
```

### View Logs
```bash
# All services
docker compose -f docker-compose.production.yml logs -f

# Specific service
docker compose -f docker-compose.production.yml logs -f backend
```

### Restart Services
```bash
docker compose -f docker-compose.production.yml restart
```

### Update Application
```bash
cd /opt/troubleshooting-ai-demo
git pull origin main
./scripts/deploy-production.sh
```

## Troubleshooting

### Services not starting
```bash
# Check logs
docker compose -f docker-compose.production.yml logs

# Check container status
docker compose -f docker-compose.production.yml ps
```

### Database connection issues
```bash
# Check postgres is running
docker compose -f docker-compose.production.yml ps postgres

# Check database connection
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "SELECT 1;"
```

### Nginx issues
```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

### SSL certificate issues
```bash
# Renew certificates
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

## Security Checklist

- [ ] All default passwords changed
- [ ] Strong SECRET_KEY generated
- [ ] Strong CREDENTIAL_ENCRYPTION_KEY generated
- [ ] Database password is strong
- [ ] HTTPS enabled (SSL certificates)
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] Database not exposed externally
- [ ] Redis not exposed externally
- [ ] DEBUG=false in production
- [ ] ALLOWED_HOSTS restricted to your domains
- [ ] Backend subdomain IP restricted (if exposing)

## Next Steps After Deployment

1. Set up automated backups
2. Configure monitoring/alerting
3. Set up log aggregation
4. Document access credentials securely
5. Test disaster recovery process

