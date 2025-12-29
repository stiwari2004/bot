# PostgreSQL Port Coexistence Guide

## Problem
Two applications need PostgreSQL:
- **Resolvify (resolvify.tech)**: Uses Docker Compose with PostgreSQL
- **Strapi (admin.fitglide.in)**: Uses host PostgreSQL on port 5432

Both were trying to use port 5432, causing conflicts.

## Solution

### Resolvify Configuration (Docker)
- **Internal Docker Network**: `postgres:5432` (container-to-container)
- **Host Port**: NOT exposed (no port mapping)
- **Connection**: Backend connects via Docker service name `postgres:5432`

### Strapi Configuration (Host)
- **Host Port**: `localhost:5432` (or `127.0.0.1:5432`)
- **Connection**: Strapi connects directly to host PostgreSQL service

## How They Coexist

```
┌─────────────────────────────────────────────────┐
│ Host System (Ubuntu Server)                     │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ Strapi (admin.fitglide.in)              │   │
│  │ Connects to: localhost:5432              │   │
│  └──────────────────────────────────────────┘   │
│           │                                       │
│           ▼                                       │
│  ┌──────────────────────────────────────────┐   │
│  │ Host PostgreSQL Service                   │   │
│  │ Port: 5432 (host)                         │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ Docker Network (bot_app-network)         │   │
│  │                                           │   │
│  │  ┌──────────────┐    ┌──────────────┐    │   │
│  │  │ Backend      │───▶│ PostgreSQL   │    │   │
│  │  │ Container    │    │ Container    │    │   │
│  │  │              │    │ (no host    │    │   │
│  │  │              │    │  port)       │    │   │
│  │  └──────────────┘    └──────────────┘    │   │
│  │                                           │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Configuration Files

### docker-compose.production.yml
```yaml
postgres:
  image: pgvector/pgvector:pg15
  # NO port mapping - only accessible within Docker network
  # ports:
  #   - "5432:5432"  # COMMENTED OUT
  networks:
    - app-network

backend:
  environment:
    # Connects via Docker service name, not host port
    - DATABASE_URL=postgresql://postgres:password@postgres:5432/troubleshooting_ai
```

### Strapi Configuration
```javascript
// Strapi database config
{
  connection: {
    host: 'localhost',  // or '127.0.0.1'
    port: 5432,
    database: 'strapi_db',
    // ...
  }
}
```

## Verification

### Check Resolvify PostgreSQL (Docker)
```bash
# Should show NO port mapping
docker-compose -f docker-compose.production.yml ps postgres

# Should show: (no ports listed or only internal)
```

### Check Strapi PostgreSQL (Host)
```bash
# Should show host service on port 5432
sudo systemctl status postgresql
sudo lsof -i :5432
```

### Test Connections

**From Resolvify backend container:**
```bash
docker exec bot_backend_1 psql -h postgres -U postgres -d troubleshooting_ai -c "SELECT 1;"
```

**From host (Strapi):**
```bash
psql -h localhost -U strapi_user -d strapi_db -c "SELECT 1;"
```

## Troubleshooting

### If Strapi can't connect:
1. Check host PostgreSQL is running: `sudo systemctl status postgresql`
2. Check port 5432 is listening: `sudo lsof -i :5432`
3. Check firewall: `sudo ufw status`
4. Check PostgreSQL config: `/etc/postgresql/*/main/postgresql.conf`

### If Resolvify can't connect:
1. Check Docker network: `docker network inspect bot_app-network`
2. Check backend logs: `docker-compose -f docker-compose.production.yml logs backend`
3. Verify DATABASE_URL uses service name: `postgres:5432` (not `localhost:5432`)

## Important Notes

1. **Resolvify backend** uses Docker service name `postgres` (resolves to container IP)
2. **Strapi** uses `localhost` (resolves to host IP)
3. **No port conflict** because Resolvify PostgreSQL doesn't expose host port
4. **Both can run simultaneously** without issues

## Quick Fix Script

Run this to ensure correct configuration:
```bash
./scripts/fix-postgres-port-conflict.sh
```



