# New SSL Certificate for resolvify.tech

Your nginx configs use:
- **resolvify.tech** cert at `/etc/letsencrypt/live/resolvify.tech/` (main site, dev, admin)
- **demo.resolvify.tech** cert at `/etc/letsencrypt/live/demo.resolvify.tech/` (demo only)

Run these commands **on the server** (where nginx and the domain DNS point).

---

## 1. Install certbot (if needed)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

**Or use snap:**
```bash
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

---

## 2. Obtain a new certificate for resolvify.tech

Use the **nginx** plugin so certbot configures the server block and gets the cert.  
Ensure nginx is running and port 80 is open for the HTTP-01 challenge.

**Option A – New cert (certonly) for resolvify.tech (+ www):**
```bash
sudo certbot certonly --nginx \
  -d resolvify.tech \
  -d www.resolvify.tech \
  --non-interactive --agree-tos \
  --email YOUR_EMAIL@example.com
```

Replace `YOUR_EMAIL@example.com` with your real email (for expiry notices).

**Option B – Force renew existing cert (same paths, new cert):**
```bash
sudo certbot renew --force-renewal --cert-name resolvify.tech
```

**Option C – Include dev in the same cert (one cert for main + dev):**
```bash
sudo certbot certonly --nginx \
  -d resolvify.tech \
  -d www.resolvify.tech \
  -d dev.resolvify.tech \
  --non-interactive --agree-tos \
  --email YOUR_EMAIL@example.com
```

Cert and key will be in:
- `/etc/letsencrypt/live/resolvify.tech/fullchain.pem`
- `/etc/letsencrypt/live/resolvify.tech/privkey.pem`

Your existing nginx configs already point there, so no nginx changes are needed.

---

## 3. Reload nginx

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 4. (Optional) New cert for demo.resolvify.tech

If you also want a new cert for demo:

```bash
sudo certbot certonly --nginx \
  -d demo.resolvify.tech \
  --non-interactive --agree-tos \
  --email YOUR_EMAIL@example.com
```

Then reload nginx as in step 3.

---

## Troubleshooting

- **“Certificate not accepted” in browser:** After creating/renewing, hard-refresh (Ctrl+Shift+R) or try another device; confirm you’re hitting the right host (resolvify.tech vs www vs dev).
- **Certbot fails (e.g. “connection refused”):** Ensure nginx is running, port 80 is open, and DNS for resolvify.tech points to this server.
- **Nginx fails after certbot:** Run `sudo nginx -t` and fix any config errors; certbot may have added a duplicate server block—edit `/etc/nginx/sites-enabled/` and remove duplicates if needed.
- **Rate limits:** Let’s Encrypt has a limit on how often you can issue certs per domain; avoid running `--force-renewal` too often.

---

## Auto-renewal (recommended)

Certbot installs a timer/cron. Test renewal with:

```bash
sudo certbot renew --dry-run
```

If that succeeds, renewal will run automatically before expiry.
