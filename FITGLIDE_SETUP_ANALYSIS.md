# Fitglide/Strapi Setup Analysis

## Current Understanding

### Resolvify Setup (What We Know)
- **PostgreSQL**: Docker container, internal network only (`postgres:5432`)
- **Connection Method**: Direct Docker network connection (NOT proxied)
- **Nginx Proxy**: Only for HTTP/HTTPS (frontend/backend), NOT database
- **Backend Connection**: `postgresql://postgres:password@postgres:5432/troubleshooting_ai`

### Fitglide/Strapi Setup (What We Need to Check)

## Information Needed

To determine if Fitglide needs PostgreSQL proxying, I need:

### 1. **Deployment Method**
   - [ ] Is Strapi running in Docker containers?
   - [ ] Is Strapi running directly on the host?
   - [ ] Is Strapi using PM2, systemd, or another process manager?

**Check with:**
```bash
# Docker containers
docker ps | grep -i strapi

# Host processes
ps aux | grep -i strapi
systemctl list-units | grep -i strapi
```

### 2. **PostgreSQL Location**
   - [ ] Is Strapi's PostgreSQL in Docker?
   - [ ] Is Strapi's PostgreSQL on the host?
   - [ ] What port is Strapi's PostgreSQL using?

**Check with:**
```bash
# Docker PostgreSQL
docker ps | grep postgres

# Host PostgreSQL
sudo systemctl status postgresql
sudo lsof -i :5432
```

### 3. **Strapi Database Configuration**
   - [ ] Where is Strapi's config file?
   - [ ] What is the DATABASE_URL or connection string?
   - [ ] How does Strapi connect to PostgreSQL?

**Check with:**
```bash
# Find Strapi config
find /home /opt /var/www -name "database.js" -o -name "database.json" 2>/dev/null

# Check Strapi .env file
find /home /opt /var/www -name ".env" -path "*/strapi*" 2>/dev/null
```

### 4. **Nginx Configuration for Fitglide**
   - [ ] Is there an nginx config for admin.fitglide.in?
   - [ ] Does it proxy to Strapi?
   - [ ] Is there any database proxying?

**Check with:**
```bash
# Nginx configs
ls -la /etc/nginx/sites-available/ | grep fitglide
ls -la /etc/nginx/conf.d/ | grep fitglide
grep -r "fitglide\|admin.fitglide" /etc/nginx/
```

## Scenarios

### Scenario A: Strapi in Docker, PostgreSQL in Docker
**Solution**: Similar to Resolvify
- Use Docker internal network
- No port exposure needed
- No nginx proxying needed for database

### Scenario B: Strapi on Host, PostgreSQL on Host
**Solution**: Direct connection
- Strapi connects to `localhost:5432`
- No proxying needed
- This is the current assumption

### Scenario C: Strapi in Docker, PostgreSQL on Host
**Solution**: Connect via host network
- Use `host.docker.internal:5432` or `172.17.0.1:5432`
- Or use host network mode
- No nginx proxying needed

### Scenario D: Strapi on Host, PostgreSQL in Docker
**Solution**: Expose Docker port or use host network
- Expose PostgreSQL port: `5432:5432` (but conflicts with Resolvify)
- Or use host network mode for PostgreSQL container
- No nginx proxying needed

## Key Point: PostgreSQL Proxying is NOT Needed

**Important**: PostgreSQL connections are **NOT** proxied through nginx. They are:
- Direct TCP connections
- Internal Docker network connections (for Docker-to-Docker)
- Direct host connections (for host-to-host)

Nginx only proxies:
- HTTP/HTTPS traffic
- Web requests (frontend/backend APIs)
- NOT database connections

## What We're Actually Checking

The real question is: **Do Resolvify and Fitglide need to share PostgreSQL, or do they need separate instances?**

If they need separate instances:
- Resolvify: Docker PostgreSQL (internal network)
- Fitglide: Host PostgreSQL (port 5432)
- ✅ No conflict (different network namespaces)

If they need to share:
- Both connect to same PostgreSQL instance
- Need to ensure port access is correct
- May need connection pooling

## Next Steps

1. Run the diagnostic script: `./scripts/check-fitglide-setup.sh`
2. Share the output
3. Check Strapi's database configuration file
4. Determine if they need separate or shared PostgreSQL



