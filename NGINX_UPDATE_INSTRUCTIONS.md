# Nginx Configuration Update Instructions

## ⚠️ Important: Backup First!

Before making any changes, backup your existing nginx configs:

```bash
# Backup existing configs
sudo cp /etc/nginx/sites-available/resolvify.tech /etc/nginx/sites-available/resolvify.tech.backup
sudo cp /etc/nginx/sites-available/demo.resolvify.tech /etc/nginx/sites-available/demo.resolvify.tech.backup 2>/dev/null || echo "Demo config doesn't exist"
sudo cp /etc/nginx/sites-available/admin.resolvify.tech /etc/nginx/sites-available/admin.resolvify.tech.backup 2>/dev/null || echo "Admin config doesn't exist"
```

## Option 1: Manual Update (Recommended)

Edit your existing nginx configs to add the `/api` location block:

### For resolvify.tech (main app):

```bash
sudo nano /etc/nginx/sites-available/resolvify.tech
```

**Add this location block BEFORE the `location /` block:**

```nginx
    # Proxy API requests to backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy health check to backend
    location /health {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

**Your existing `location /` block should already proxy to `http://localhost:3004` - keep that as is.**

### For demo.resolvify.tech:

If you have a separate config for demo, add the same `/api` and `/health` blocks there too.

### For admin.resolvify.tech:

If you have a separate config for admin, add the same `/api` and `/health` blocks there too.

## Option 2: View Reference Configs

You can view the reference configs from the repo:

```bash
cd /home/opsbot/bot
cat nginx/resolvify-tech-main.conf
cat nginx/resolvify-tech-demo.conf
cat nginx/resolvify-tech-admin.conf
```

Then manually merge the `/api` and `/health` location blocks into your existing configs.

## After Making Changes

```bash
# Test nginx config
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

## Verify It Works

```bash
# Test main app health
curl https://resolvify.tech/health

# Test main app API
curl https://resolvify.tech/api/v1/test/health-detailed
```

## Rollback (If Needed)

If something goes wrong:

```bash
# Restore from backup
sudo cp /etc/nginx/sites-available/resolvify.tech.backup /etc/nginx/sites-available/resolvify.tech
sudo nginx -t
sudo systemctl reload nginx
```

