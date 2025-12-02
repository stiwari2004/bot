# Quick Deployment Guide - Public Sandbox

**Goal**: Get your sandbox live in 30-60 minutes

---

## 🚀 Option 1: Railway (Easiest - Recommended)

### Step 1: Prepare Code (5 minutes)

1. **Generate Secrets**:
   ```bash
   # SECRET_KEY (32+ characters)
   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   
   # CREDENTIAL_ENCRYPTION_KEY (Fernet key)
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

2. **Update `docker-compose.sandbox.yml`**:
   ```yaml
   backend-sandbox:
     environment:
       - DEBUG=false  # ← Change
       - RATE_LIMIT_ENABLED=true  # ← Change
       - SECRET_KEY=${SECRET_KEY}  # ← Use env var
       - CREDENTIAL_ENCRYPTION_KEY=${CREDENTIAL_ENCRYPTION_KEY}  # ← Use env var
       - ALLOWED_HOSTS=["*"]  # ← For public access
       - ENVIRONMENT=production
   ```

### Step 2: Deploy to Railway (15 minutes)

1. **Sign up**: https://railway.app (free tier available)
2. **New Project** → "Deploy from GitHub repo"
3. **Select your repository**
4. **Add Services**:
   - **PostgreSQL** (Railway managed)
   - **Redis** (Railway managed or use Upstash)
   - **Backend** (from Dockerfile)
   - **Frontend** (from Dockerfile)

5. **Set Environment Variables** (for backend):
   ```
   SECRET_KEY=<your-generated-secret-key>
   CREDENTIAL_ENCRYPTION_KEY=<your-generated-fernet-key>
   DATABASE_URL=<railway-postgres-url>
   REDIS_URL=<railway-redis-url>
   DEBUG=false
   RATE_LIMIT_ENABLED=true
   ALLOWED_HOSTS=["*"]
   ENVIRONMENT=production
   ```

6. **Set Environment Variables** (for frontend):
   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app
   ```

7. **Deploy!** Railway will automatically:
   - Build Docker images
   - Set up HTTPS
   - Provide public URLs

### Step 3: Seed Database (5 minutes)

1. **Connect to backend container**:
   ```bash
   railway run --service backend python scripts/seed_sandbox_data.py
   ```

2. **Verify**: Check logs for "✅ Seeding complete"

### Step 4: Test (5 minutes)

1. Visit frontend URL (provided by Railway)
2. Test login: `demo@example.com` / `demo123`
3. Test demo mode (skip login)
4. Verify API endpoints work

**Done!** 🎉 Your sandbox is live!

---

## 🚀 Option 2: Render (Alternative)

### Similar to Railway:

1. **Sign up**: https://render.com
2. **New Web Service** → Connect GitHub
3. **Configure**:
   - **Build Command**: `docker-compose -f docker-compose.sandbox.yml build`
   - **Start Command**: `docker-compose -f docker-compose.sandbox.yml up`
   - **Environment**: Docker

4. **Add PostgreSQL** (Render managed)
5. **Add Redis** (Render managed)
6. **Set environment variables** (same as Railway)
7. **Deploy**

**Pros**: Free tier, automatic HTTPS, easy setup  
**Cons**: Slightly more complex than Railway

---

## 🚀 Option 3: DigitalOcean App Platform

1. **Sign up**: https://www.digitalocean.com
2. **Create App** → GitHub integration
3. **Add Components**:
   - PostgreSQL (managed)
   - Redis (managed)
   - Backend (Docker)
   - Frontend (Docker)

4. **Configure environment variables**
5. **Deploy**

**Pros**: Good performance, reliable  
**Cons**: Paid (starts at $5/month)

---

## 🔧 Manual VPS Deployment (More Control)

### Prerequisites
- VPS (Ubuntu 22.04) - DigitalOcean, Linode, AWS EC2
- Domain name (optional but recommended)
- SSH access

### Steps

1. **Install Docker & Docker Compose**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo apt-get install docker-compose-plugin
   ```

2. **Clone Repository**:
   ```bash
   git clone <your-repo-url>
   cd bot
   ```

3. **Create `.env` file**:
   ```bash
   cd backend
   cp env.example .env
   # Edit .env with your secrets
   ```

4. **Update `docker-compose.sandbox.yml`** with production settings

5. **Deploy**:
   ```bash
   docker-compose -f docker-compose.sandbox.yml up -d
   ```

6. **Set up Nginx + Let's Encrypt** (for HTTPS):
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

7. **Seed Database**:
   ```bash
   docker-compose -f docker-compose.sandbox.yml exec backend-sandbox python scripts/seed_sandbox_data.py
   ```

---

## ✅ Post-Deployment Checklist

- [ ] HTTPS is working (check browser padlock)
- [ ] Login works (`demo@example.com` / `demo123`)
- [ ] Demo mode works (skip login)
- [ ] API endpoints respond
- [ ] WebSocket connections work
- [ ] File uploads work
- [ ] Database is seeded with demo data
- [ ] Rate limiting is active (test with rapid requests)
- [ ] Error pages don't expose sensitive info (DEBUG=false)

---

## 🐛 Troubleshooting

### Issue: CORS errors
**Fix**: Ensure `ALLOWED_HOSTS` includes your frontend domain

### Issue: Database connection fails
**Fix**: Check `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`

### Issue: Frontend can't reach backend
**Fix**: Set `NEXT_PUBLIC_API_BASE_URL` to backend's public URL

### Issue: 401 Unauthorized
**Fix**: Check if `SECRET_KEY` is set correctly

### Issue: Slow first request
**Fix**: Set `PRELOAD_EMBEDDING_MODEL=true` (uses more memory)

---

## 📊 Cost Estimates

| Platform | Monthly Cost | Notes |
|----------|--------------|-------|
| **Railway** | $0-20 | Free tier available, pay-as-you-go |
| **Render** | $0-25 | Free tier, then $7/service |
| **DigitalOcean** | $5-40 | $5 base + services |
| **VPS (DO/Linode)** | $6-40 | Full control, manual setup |
| **AWS/GCP** | $10-50 | Pay-as-you-go, more complex |

**Recommendation**: Start with Railway (free tier) for testing, then scale up if needed.

---

## 🎯 Next Steps After Deployment

1. **Monitor Usage**: Set up basic analytics
2. **Add Monitoring**: Sentry for error tracking
3. **Set Up Backups**: Automated database backups
4. **Custom Domain**: Configure your own domain
5. **Documentation**: Create user guide for sandbox

---

## 🆘 Need Help?

If you encounter issues:
1. Check application logs: `railway logs` or `docker-compose logs`
2. Verify environment variables are set correctly
3. Test database connection separately
4. Check CORS configuration matches your domain

**You're almost there!** 🚀



