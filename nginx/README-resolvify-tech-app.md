# resolvify.tech: Marketing site + customer slug (URL stays resolvify.tech)

## Goal

- **https://resolvify.tech** → marketing site (static)
- **https://resolvify.tech?customer_slug=konverge** → app (customer portal) on **the same host**; URL stays resolvify.tech?customer_slug=konverge (no redirect to demo)

## How it works

1. **`location = /`** – If the request has `?customer_slug=*`, **proxy** to the gateway (8080) so the app is served; the browser URL does not change. If no customer_slug, serve marketing (try_files).
2. **`location /_next/`** – Proxy to 8080 so the app’s JS/CSS (/_next/*) load on resolvify.tech.
3. **`location /app`** – Optional; proxy to 8080 so resolvify.tech/app?customer_slug=* also works (gateway rewrites /app → /).

## Nginx (resolvify.tech server block)

Use the `resolvify-tech-with-app.conf` logic:

- **`location = /`** with an `if ($arg_customer_slug != "")` block that does `proxy_pass http://127.0.0.1:8080` and proxy headers (and `break`), else `try_files /index.html =404`.
- **`location /_next/`** with `proxy_pass http://127.0.0.1:8080` and the same proxy headers.
- **`location /api/`** to your backend (e.g. 8000).
- **`location /`** (catch‑all) to marketing `try_files`.

Reload: `sudo nginx -t && sudo systemctl reload nginx`.

## Summary

| URL | Result |
|-----|--------|
| https://resolvify.tech | Marketing (static) |
| https://resolvify.tech?customer_slug=konverge | App (proxied to 8080); **URL stays resolvify.tech?customer_slug=konverge** |
| https://resolvify.tech/app?customer_slug=konverge | App (proxied to 8080) |
| https://resolvify.tech/_next/* | App assets (proxied to 8080) |
| https://resolvify.tech/api/* | Backend (e.g. 8000) |
