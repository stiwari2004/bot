## PaaS / Self‑Hosted Deployment Guide

**Goal**: Run a single‑tenant instance of the Troubleshooting AI Agent on your own infrastructure (VM, bare metal, or your own Kubernetes cluster) using the existing Docker images and `docker-compose` files.

This guide assumes:
- You are comfortable with basic Linux and Docker commands
- You have a VM (Ubuntu 22.04 or similar) or equivalent host

---

## 1. Provision a Host

- **CPU**: 4 vCPUs (minimum 2 for small tests)
- **RAM**: 8 GB recommended (can work on 4 GB with `docker-compose.optimized.yml`)
- **Disk**: 50+ GB SSD
- **OS**: Ubuntu 22.04 LTS (or similar)

---

## 2. Install Docker & Docker Compose

On the host:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install -y docker-compose-plugin
```

Verify:

```bash
docker --version
docker compose version
```

---

## 3. Clone the Repository

```bash
git clone <your-repo-url> bot
cd bot
```

---

## 4. Configure Backend Environment

The backend reads configuration from environment variables / `.env`. You have **three options**:

### Option A: Interactive Setup Script (Recommended) ⭐

**For Linux/Mac:**
```bash
./scripts/setup-paas.sh
```

**For Windows:**
```powershell
.\scripts\setup-paas.ps1
```

The script will:
- ✅ Guide you through all configuration options
- ✅ Auto-generate secure keys (SECRET_KEY, CREDENTIAL_ENCRYPTION_KEY)
- ✅ Create a complete `.env` file with sensible defaults
- ✅ Backup existing `.env` if present

**After running the script**, review the generated `.env` file and adjust if needed.

### Option B: Manual Configuration

A sample `.env` template is already provided.

```bash
cd backend
cp env.example .env
```

Then edit `.env` manually and set at least:

- **Database (if using external DB)**  
  - `DATABASE_URL=postgresql://user:password@host:5432/troubleshooting_ai`

- **Security**  
  - `SECRET_KEY=` (32+ chars; JWT signing key)
  - `CREDENTIAL_ENCRYPTION_KEY=` (Fernet key)

  Generate:

  ```bash
  python -c 'import secrets; print(secrets.token_urlsafe(32))'  # SECRET_KEY
  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'  # CREDENTIAL_ENCRYPTION_KEY
  ```

- **Environment**  
  - `ENVIRONMENT=production`
  - `ALLOWED_HOSTS=["https://your-frontend-domain", "https://your-backend-domain"]`

For a simple single‑VM deployment using the bundled Postgres and Redis in Docker, you can keep:

- `DATABASE_URL=postgresql://postgres:CHANGE_ME_STRONG_PASSWORD@localhost:5432/troubleshooting_ai`
- `REDIS_URL=redis://localhost:6379/0`

> For a real deployment, change passwords and secrets to strong values.

---

## 5. Choose a Compose File

You have two main options:

- **`docker-compose.yml`** – standard dev / prod‑like stack
- **`docker-compose.optimized.yml`** – same stack with lower memory limits (better for 4–8 GB hosts)

For PaaS / self‑hosted, the **optimized** file is usually a good default:

```bash
cd /path/to/bot
docker compose -f docker-compose.optimized.yml up -d
```

This will start:
- Postgres (with pgvector)
- Redis
- Backend (FastAPI)
- Worker
- Frontend (Next.js)

Ports (by default):
- Backend API: `http://<host>:8000`
- Frontend: `http://<host>:3000`
- Postgres: `5432` (local only, unless firewalled)

---

## 6. Frontend → Backend Configuration

The optimized compose file already wires the frontend to the backend via Docker network:

- `NEXT_PUBLIC_API_BASE_URL=http://backend:8000`

For an external load balancer / reverse proxy:
- Expose `:3000` (frontend) publicly
- Keep `:8000` either internal or behind the same reverse proxy

If you run the frontend separately (e.g., different host), set:

```bash
export NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain
```

in the frontend environment (or in the PaaS provider’s env settings).

---

## 7. First‑Time DB Setup / Seeding (Optional)

If you want demo data:

```bash
docker compose exec backend python scripts/seed_sandbox_data.py
```

If you only want a clean, empty system for your own tenants/customers, **skip seeding**.

---

## 8. Basic Health Checks

From your browser or a tool like `curl`:

- **API docs**: `http://<host>:8000/docs`
- **Frontend**: `http://<host>:3000`

Expected:
- You can load the login / demo page
- `/docs` shows FastAPI swagger UI

---

## 9. Production Hardening Checklist (PaaS)

Before treating this as a serious self‑hosted deployment:

- **Secrets & config**
  - [ ] Change all default passwords and keys (`SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, DB password)
  - [ ] Set `ENVIRONMENT=production`
  - [ ] Set `DEBUG=false` (in env, if used)
  - [ ] Restrict `ALLOWED_HOSTS` to your real domains

- **Networking**
  - [ ] Put an HTTP reverse proxy (nginx/Traefik) in front of the frontend/backend
  - [ ] Enable HTTPS (Let’s Encrypt)
  - [ ] Restrict direct DB access (firewall / security group)

- **Data**
  - [ ] Configure automated Postgres backups
  - [ ] Monitor disk usage for `/var/lib/docker` and Postgres volumes

- **Monitoring**
  - [ ] Configure basic logs/metrics collection for the containers

---

## 10. Using a Cloud PaaS (Railway / Render / DigitalOcean)

For platforms like Railway/Render/DO App Platform:

- Use the existing `backend/Dockerfile` and `frontend-nextjs/Dockerfile`
- Provision managed Postgres + Redis
- Set environment variables as documented in `QUICK_DEPLOYMENT_GUIDE.md`
- Build and start services from Dockerfiles instead of `docker-compose` if the platform prefers that model

That path is already described in more detail in `QUICK_DEPLOYMENT_GUIDE.md`.

---

## 11. High‑Level PaaS Story (What You Can Tell Customers)

- “You can deploy this as a **single‑tenant instance** on your own infra using Docker Compose.”
- Requirements:
  - A VM (4–8 GB RAM, 4 vCPUs)
  - Docker + docker compose plugin
  - One command: `docker compose -f docker-compose.optimized.yml up -d`
- Configurable via:
  - `backend/.env` (secrets, DB, LLM URL, CORS)
  - Environment variables in your PaaS of choice

This completes the **PaaS fundamentals**: Docker images, compose files, environment template, and a clear deployment recipe.


