# Quick Deployment Guide - 20-30 Minutes (Hostinger)

## Prerequisites Checklist
- [ ] Hostinger VPS/Server access (SSH)
- [ ] DNS A records configured (demo, dev, admin, backend → server IP)
- [ ] Domain name ready
- [ ] API keys ready (GEMINI_API_KEY, PERPLEXITY_API_KEY)

## Step 1: Server Setup (5 minutes)

### SSH into your Hostinger server
```bash
ssh user@your-server-ip
```

### Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Install Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Log out and back in (or run: newgrp docker)
exit
# SSH back in
```

## Step 2: Clone Repository (2 minutes)

```bash
# Create directory
sudo mkdir -p /opt/troubleshooting-ai-demo
sudo chown $USER:$USER /opt/troubleshooting-ai-demo
cd /opt/troubleshooting-ai-demo

# Clone your repo
git clone <your-repo-url> .

# Make scripts executable
chmod +x scripts/*.sh
```

## Step 3: Configure Environment (5 minutes)

### Backend Configuration
```bash
cd /opt/troubleshooting-ai-demo/backend
cp env.example .env
nano .env
```

**Quick copy-paste for .env (replace YOUR_DOMAIN and generate secrets):**
```bash
# Database
DATABASE_URL=postgresql://postgres:CHANGE_ME_STRONG_PASSWORD@postgres:5432/troubleshooting_ai

# Security (GENERATE THESE!)
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
CREDENTIAL_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# Add to .env:
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=["https://demo.YOUR_DOMAIN.com", "https://admin.YOUR_DOMAIN.com"]

# API Keys
GEMINI_API_KEY=your_gemini_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here

# Other settings
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
CHUNK_SIZE=512
CHUNK_OVERLAP=50
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
MAX_FILE_SIZE=104857600
UPLOAD_DIR=uploads
```

**Generate secrets quickly:**
```bash
# Run these and copy output to .env
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_urlsafe(32))'
python3 -c 'from cryptography.fernet import Fernet; print("CREDENTIAL_ENCRYPTION_KEY=" + Fernet.generate_key().decode())'
```

### Update docker-compose.production.yml
```bash
cd /opt/troubleshooting-ai-demo
nano docker-compose.production.yml
```

**Change this line (around line 10):**
```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-YOUR_STRONG_PASSWORD_HERE}
```

### Frontend Configuration
```bash
cd /opt/troubleshooting-ai-demo/frontend-nextjs
echo "NEXT_PUBLIC_API_BASE_URL=https://demo.YOUR_DOMAIN.com/api" > .env.production
# Replace YOUR_DOMAIN with your actual domain
```

## Step 4: Configure Nginx (5 minutes)

### Copy and update nginx configs
```bash
cd /opt/troubleshooting-ai-demo

# Copy configs
sudo cp nginx/troubleshooting-ai-demo.conf /etc/nginx/sites-available/
sudo cp nginx/troubleshooting-ai-admin.conf /etc/nginx/sites-available/

# Replace yourdomain.com with YOUR actual domain
sudo sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/troubleshooting-ai-*.conf

# Enable sites
sudo ln -s /etc/nginx/sites-available/troubleshooting-ai-demo /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/troubleshooting-ai-admin /etc/nginx/sites-enabled/

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 5: Get SSL Certificates (3 minutes)

```bash
# Get SSL for demo subdomain
sudo certbot --nginx -d demo.YOUR_DOMAIN.com --non-interactive --agree-tos --email your-email@example.com

# Get SSL for admin subdomain
sudo certbot --nginx -d admin.YOUR_DOMAIN.com --non-interactive --agree-tos --email your-email@example.com
```

## Step 6: Deploy Application (5 minutes)

```bash
cd /opt/troubleshooting-ai-demo

# Build and start
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d

# Wait a moment
sleep 15

# Check status
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs --tail=50
```

## Step 7: Initialize Database & Seed Demo Data (3 minutes)

```bash
cd /opt/troubleshooting-ai-demo

# Initialize database (creates tables)
docker compose -f docker-compose.production.yml exec backend python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
"

# Seed demo data (if you have a seed script)
docker compose -f docker-compose.production.yml exec backend python scripts/seed_sandbox_data.py 2>/dev/null || echo "No seed script, skipping"
```

## Step 8: Verify (2 minutes)

### Test URLs
```bash
# Check backend health
curl https://demo.YOUR_DOMAIN.com/api/health

# Check frontend
curl -I https://demo.YOUR_DOMAIN.com
```

### Test in Browser
1. Open: `https://demo.YOUR_DOMAIN.com`
2. Should see login page
3. Test login: `demo@example.com` / `demo123` (if seeded)
4. Or use "Skip Login" for demo mode

## Troubleshooting Quick Fixes

### Services not starting?
```bash
docker compose -f docker-compose.production.yml logs
docker compose -f docker-compose.production.yml restart
```

### Nginx errors?
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Database connection issues?
```bash
# Check postgres is running
docker compose -f docker-compose.production.yml ps postgres

# Check connection
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "SELECT 1;"
```

### Port conflicts?
```bash
# Check what's using ports
sudo netstat -tulpn | grep -E ':(3000|8000|5432)'
```

## Quick Commands Reference

```bash
# View logs
docker compose -f docker-compose.production.yml logs -f

# Restart services
docker compose -f docker-compose.production.yml restart

# Stop services
docker compose -f docker-compose.production.yml down

# Start services
docker compose -f docker-compose.production.yml up -d

# Update application
cd /opt/troubleshooting-ai-demo
git pull
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

## Security Quick Checklist

- [ ] Changed POSTGRES_PASSWORD in docker-compose.production.yml
- [ ] Generated SECRET_KEY (32+ chars)
- [ ] Generated CREDENTIAL_ENCRYPTION_KEY
- [ ] Set DEBUG=false
- [ ] SSL certificates installed
- [ ] Firewall configured (ports 22, 80, 443 only)

## You're Live! 🎉

Your application should now be accessible at:
- **Main App**: https://demo.YOUR_DOMAIN.com
- **Admin**: https://admin.YOUR_DOMAIN.com (redirects to /super-admin)
- **API Docs**: https://demo.YOUR_DOMAIN.com/api/docs

---

**Total Time: ~20-30 minutes**

