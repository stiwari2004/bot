# Environment Differences: Sandbox vs Regular

## Overview

This project has two separate environments that can run simultaneously:

1. **Regular Environment** (Main/Production-like)
2. **Sandbox Environment** (Isolated Testing)

---

## Regular Environment

### Configuration
- **Backend Port**: `8000`
- **Frontend Port**: `3000`
- **Database**: `troubleshooting_ai` (PostgreSQL on port `5432`)
- **Redis**: Port `6379`
- **Docker Compose File**: `docker-compose.yml`

### Purpose
- Main development environment
- Production-like setup
- Persistent data storage
- Full feature set enabled

### Usage
```bash
# Start regular environment
docker-compose up -d

# Access
Frontend: http://localhost:3000
Backend: http://localhost:8000
API Docs: http://localhost:8000/docs
```

---

## Sandbox Environment

### Configuration
- **Backend Port**: `8001`
- **Frontend Port**: `3001`
- **Database**: `sandbox_db` (PostgreSQL on port `5433`)
- **Redis**: Port `6380`
- **Docker Compose File**: `docker-compose.sandbox.yml`

### Purpose
- **Isolated testing environment**
- Pre-seeded with demo data
- Safe to reset/experiment
- Separate from main data
- Perfect for demos and testing

### Pre-seeded Data
- **Demo Tenant**: `demo` (ID: 1)
- **Demo User**: 
  - Email: `demo@example.com`
  - Password: `demo123`
- **Sample Tickets**: 5-10 tickets with various statuses
- **Sample Runbooks**: Pre-approved runbooks for testing

### Usage
```bash
# Start sandbox environment
docker-compose -f docker-compose.sandbox.yml up -d

# Seed demo data (first time or after reset)
docker-compose -f docker-compose.sandbox.yml exec backend-sandbox python scripts/seed_sandbox_data.py

# Reset sandbox (drops all data and reseeds)
docker-compose -f docker-compose.sandbox.yml exec backend-sandbox python scripts/reset_sandbox.py

# Access
Frontend: http://localhost:3001
Backend: http://localhost:8001
API Docs: http://localhost:8001/docs
```

### Scripts Available
- `scripts/sandbox-start.sh` - Start sandbox
- `scripts/sandbox-stop.sh` - Stop sandbox
- `scripts/sandbox-reset.sh` - Reset and reseed sandbox

---

## Key Differences Summary

| Feature | Regular | Sandbox |
|---------|---------|---------|
| **Ports** | 8000/3000 | 8001/3001 |
| **Database** | `troubleshooting_ai` | `sandbox_db` |
| **Data** | Your actual data | Demo/test data |
| **Reset Safety** | ⚠️ Destructive | ✅ Safe to reset |
| **Use Case** | Development/Production | Testing/Demos |
| **Pre-seeded** | ❌ No | ✅ Yes |

---

## Authentication

### Login Credentials (Sandbox Only)
- **Email**: `demo@example.com`
- **Password**: `demo123`

### Demo Mode
- The application can run in **demo mode** without authentication
- Demo mode uses `/api/v1/demo/*` endpoints
- No login required for basic functionality
- Login provides access to authenticated endpoints and user-specific data

### Login Page
- Accessible when you first load the application
- Located at: `http://localhost:3001` (sandbox) or `http://localhost:3000` (regular)
- You can skip login to use demo mode
- Login is required for:
  - User-specific data
  - Authenticated API endpoints
  - Multi-tenant features

---

## When to Use Which?

### Use Regular Environment When:
- ✅ Developing new features
- ✅ Working with production-like data
- ✅ Testing production configurations
- ✅ Long-term data persistence needed

### Use Sandbox Environment When:
- ✅ Demonstrating the application
- ✅ Testing new features safely
- ✅ Learning/exploring the system
- ✅ Need to reset data frequently
- ✅ Want pre-populated sample data

---

## Running Both Simultaneously

You can run both environments at the same time! They use different ports and databases, so they won't interfere with each other.

```bash
# Terminal 1: Regular environment
docker-compose up -d

# Terminal 2: Sandbox environment
docker-compose -f docker-compose.sandbox.yml up -d
```

Then access:
- Regular: http://localhost:3000
- Sandbox: http://localhost:3001

---

## Troubleshooting

### Port Conflicts
If you get port conflicts, make sure:
- Regular environment uses: 3000, 8000, 5432, 6379
- Sandbox uses: 3001, 8001, 5433, 6380

### Database Issues
- Regular DB: `postgres:5432/troubleshooting_ai`
- Sandbox DB: `postgres-sandbox:5432/sandbox_db`

### Frontend Not Connecting
- Check `NEXT_PUBLIC_API_BASE_URL` environment variable
- Sandbox frontend should point to: `http://localhost:8001`
- Regular frontend should point to: `http://localhost:8000`

---

## Next Steps

1. **Start Sandbox**: `docker-compose -f docker-compose.sandbox.yml up -d`
2. **Seed Data**: Wait for containers to start, then seed data
3. **Access Frontend**: http://localhost:3001
4. **Login**: Use `demo@example.com` / `demo123` OR skip login for demo mode
5. **Explore**: All features are available with pre-seeded data!



