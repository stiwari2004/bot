# resolvify.tech: Marketing site + app with customer_slug

## Goal

- **https://resolvify.tech** → marketing site (static from resolvify-website)
- **https://resolvify.tech/?customer_slug=konverge** → tenant app (login/dashboard)

## How it works

1. Nginx redirects `/?customer_slug=*` to **/app?customer_slug=*** so the app has a dedicated path.
2. **location /app** proxies to the **same gateway as demo/admin** (`http://127.0.0.1:8080`). The gateway rewrites `/app` → `/` and forwards to the shared frontend.
3. **location /_next/** must also proxy to 8080. The app emits asset URLs like `/_next/static/...` (no `/app` prefix), so without this they would hit the marketing site and return HTML → "Unexpected token '<'" in the console.
4. The rest of `/` is served from the marketing static site.

## Steps

### 1. Nginx (host)

- Use `resolvify-tech-with-app.conf` (or merge its `location` blocks into your existing resolvify.tech server block).
- **Do not** point `location /app` at port 3000. It must point at **8080** (the same proxy gateway as demo.resolvify.tech and admin.resolvify.tech). The sample config uses `proxy_pass http://127.0.0.1:8080`.
- Reload nginx: `sudo nginx -t && sudo systemctl reload nginx`.

### 2. Gateway (Docker proxy)

The repo’s `proxy/conf.d/resolvify.conf` includes a **location /app** that strips the `/app` prefix and forwards to the frontend as `/`. So the same frontend that serves demo and admin also serves resolvify.tech/app. No separate Next.js instance on port 3000 is required.

**Optional (full SPA under /app):** If you want every app link to stay under `/app` (e.g. `/app/login`, `/app/dashboard`), run a **separate** frontend build with `NEXT_PUBLIC_BASE_PATH=/app` on its own port and point host nginx `location /app` at that port instead of 8080. With the default setup (proxy to 8080 + rewrite), `/app` and `/app/*` work when requested directly; client-side links may go to resolvify.tech/login (no `/app`) unless you use that separate build.

### 3. Links to the tenant app

- From the marketing site or emails, use:  
  **https://resolvify.tech/app?customer_slug=konverge**  
  or the redirect will work if you keep:  
  **https://resolvify.tech/?customer_slug=konverge**  
  (nginx redirects that to `/app?customer_slug=...`).

## Troubleshooting: "Unexpected token '<'" on .js / .woff2

That error means the browser requested a JS (or font) file but got HTML. Check **where** the HTML comes from.

On the server, run (use a real chunk name from the failing request in the browser Network tab):

```bash
# 1) Response from the gateway (8080) for a static asset
curl -sI -H "Host: resolvify.tech" "http://127.0.0.1:8080/_next/static/chunks/86b36876df420629.js"
```

- **200** and **Content-Type: application/javascript** → gateway is fine; the problem is the **host** nginx not sending `/_next/` to 8080 (reload host nginx, confirm `location /_next/` exists and is in the resolvify.tech server block).
- **404** or **Content-Type: text/html** → the **frontend** container is returning a 404 page for that path (rebuild/redeploy the frontend so chunk hashes match the HTML; or try a hard refresh in case of cached old HTML).

Then test through the host:

```bash
# 2) Response through host nginx (HTTPS)
curl -sI "https://resolvify.tech/_next/static/chunks/86b36876df420629.js"
```

- If (1) is JS but (2) is HTML → host nginx is not using `location /_next/` for this request (wrong server block, config not loaded, or nginx not reloaded).

After changing the **Docker** proxy config (`proxy/conf.d/resolvify.conf`), reload the proxy container so it picks up the new `location /_next/` (e.g. `docker compose -f docker-compose.production.yml restart proxy` or redeploy).

## Summary

| URL | Served by |
|-----|-----------|
| https://resolvify.tech | Marketing (static) |
| https://resolvify.tech/?customer_slug=* | Redirect → /app?customer_slug=* |
| https://resolvify.tech/app, /app/* | Next.js app (tenant login) |
| https://resolvify.tech/_next/* | Next.js app (via 8080) |
| https://resolvify.tech/api/* | Backend (e.g. 8000) |
