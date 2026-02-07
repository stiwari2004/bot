# resolvify.tech: Marketing site + app with customer_slug

## Goal

- **https://resolvify.tech** → marketing site (static from resolvify-website)
- **https://resolvify.tech/app?customer_slug=konverge** → tenant app (login/dashboard)

## Recommended: Option A (app with basePath /app on 3005)

This avoids the **"Unexpected token '<'"** error because all app URLs (including `/_next/*`) live under `/app`, so the host only needs one `location /app` and no separate `/_next/` block.

### 1. Start the app frontend (basePath /app)

```bash
cd /opt/opsbot/bot  # or your repo path
docker compose -f docker-compose.production.yml --profile resolvify-app up -d --build
```

This starts the `frontend-app` service on port **3005** (built with `NEXT_PUBLIC_BASE_PATH=/app`).

### 2. Nginx (host)

In your resolvify.tech server block use **only** `location /app` pointing at **3005** (no `location /_next/`):

```nginx
location /app {
  proxy_pass http://127.0.0.1:3005;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_connect_timeout 60s;
  proxy_read_timeout 60s;
  proxy_send_timeout 60s;
}
```

Then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Links

- **https://resolvify.tech/app?customer_slug=konverge**
- Or **https://resolvify.tech/?customer_slug=konverge** (nginx redirects to `/app?customer_slug=...`)

---

## Alternative: Option B (shared gateway 8080)

If you don’t run `frontend-app`, proxy `/app` and `/_next/` to the same gateway as demo (8080). You must have **both** `location /app` and `location /_next/` on the host; if `/_next/` is missing or wrong, the browser gets HTML instead of JS and you see "Unexpected token '<'".

- Use `resolvify-tech-with-app.conf` with the **OPTION B** blocks uncommented (location /app and location /_next/ to 8080).
- Reload the Docker proxy after changing `proxy/conf.d/resolvify.conf`.

---

## Troubleshooting: "Unexpected token '<'" on .js / .woff2

The browser requested a JS or font file but received HTML.

- **Option A (3005):** Ensure `location /app` points at `http://127.0.0.1:3005` and that the `frontend-app` container is running. No `location /_next/` is needed.
- **Option B (8080):** Run the curl checks in the repo’s README to see whether the host or the gateway is serving HTML for `/_next/*`; ensure `location /_next/` exists and nginx was reloaded.

## Summary

| URL | Served by |
|-----|-----------|
| https://resolvify.tech | Marketing (static) |
| https://resolvify.tech/?customer_slug=* | Redirect → /app?customer_slug=* |
| https://resolvify.tech/app, /app/*, /app/_next/* | Next.js app (Option A: 3005; Option B: 8080) |
| https://resolvify.tech/_next/* | Next.js app via 8080 (Option B only) |
| https://resolvify.tech/api/* | Backend (e.g. 8000) |
