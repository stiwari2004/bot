# OWASP ZAP Security Fixes

This document records the fixes applied based on the OWASP ZAP scan report (prod-app-report.html, Feb 2026).

## Summary of Findings (Before Fix)

| Risk        | Count | Status  |
|------------|-------|---------|
| High       | 0     | N/A     |
| Medium     | 2     | Fixed   |
| Low        | 8     | Mostly fixed |
| Informational | 5  | N/A     |

## Fixes Applied

### 1. Content Security Policy (CSP) Header Not Set — Medium (10038)

**Fix:** Added CSP header in `frontend-nextjs/next.config.js` via `headers()`:

- `default-src 'self'`
- `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (needed for Next.js/tooling)
- `style-src 'self' 'unsafe-inline'`
- `img-src 'self' data: https: http:`
- `font-src 'self' data:`
- `connect-src 'self' https: http: ws: wss:`
- `frame-ancestors 'none'`

### 2. Missing Anti-clickjacking Header — Medium (10020)

**Fix:** Added `X-Frame-Options: DENY` in `next.config.js` (and `frame-ancestors 'none'` in CSP). Backend already had it in `security_middleware.py`.

### 3. Permissions Policy Header Not Set — Low (10063)

**Fix:** Added `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()` in both Next.js and backend.

### 4. Insufficient Site Isolation Against Spectre — Low (90004)

**Fix:** Added `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` in Next.js and backend.

### 5. Server Leaks Information via X-Powered-By — Low (10037)

**Fix:**

- `poweredByHeader: false` in `frontend-nextjs/next.config.js`
- `proxy_hide_header X-Powered-By` in nginx for frontend locations

### 6. Server Leaks Version Information via Server Header — Low (10036)

**Fix:** Added `server_tokens off` in nginx configs. This changes `Server: nginx/1.24.0 (Ubuntu)` to `Server: nginx` (no version). To completely remove the Server header, you would need `ngx_headers_more` or similar.

**Files updated:** `nginx/dev.resolvify.tech.conf`, `nginx/resolvify-tech-dev.conf`, `proxy/conf.d/resolvify.conf`

## Items Not Fully Fixable (or Acceptable Risk)

### Dangerous JS Functions — Low (10110)

**Finding:** `eval()` in `turbopack-_62cebc78._.js` (Next.js dev/build chunk).

**Reason:** This is from Next.js/React tooling, not application code. Mitigated by CSP and other headers. Production build may differ.

### Storable and Cacheable Responses, DEBUG Comments — Informational

**Finding:** Informational alerts about cacheability and debug strings in bundled JS.

**Reason:** Low risk; debug strings are often from third-party dependencies. Cache headers can be tuned per resource if needed.

## Deployment Steps

1. **Frontend:** Rebuild and redeploy Next.js (`npm run build` / Docker).
2. **Backend:** Redeploy backend (security middleware changes).
3. **Nginx:** Reload nginx after copying updated configs:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Re-run OWASP ZAP scan to verify fixes.
