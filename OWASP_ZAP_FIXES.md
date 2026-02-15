# OWASP ZAP Security Fixes

This document records the fixes applied based on the OWASP ZAP scan reports (prod-app-report.html, Feb 2026).

## Round 2 – Remaining Findings (Post-Round 1)

| Risk        | Count | Status  |
|------------|-------|---------|
| Medium     | 5     | Partially fixed |
| Low        | 5     | Partially fixed |
| Informational | 5  | N/A     |

## Round 2 Fixes Applied

### 1. CSP: Failure to Define Directive with No Fallback — Medium (10055)

**Fix:** Added `form-action 'self'` and `base-uri 'self'` to CSP in Next.js and backend. These directives do not fall back to `default-src`.

### 2. Strict-Transport-Security Header Not Set — Low (10035)

**Fix:** Added `Strict-Transport-Security: max-age=31536000; includeSubDomains` in Next.js headers. Backend now adds HSTS for any HTTPS request (not just production).

### 3. Backend HSTS

**Fix:** Backend `security_middleware.py` adds HSTS for all HTTPS requests (dev.resolvify.tech, prod, etc.), not only when `ENVIRONMENT=production`.

## Items ZAP Will Still Flag (Accepted / Mitigated)

### CSP: script-src unsafe-eval, unsafe-inline — Medium

**Reason:** Next.js/React and tooling require these for development and many production builds. Removing them typically requires CSP nonces and build changes. Accepted risk; CSP still provides defense in depth.

### CSP: style-src unsafe-inline — Medium

**Reason:** Same as above; many React/component libraries rely on inline styles.

### CSP: Wildcard Directive (img-src, connect-src) — Medium

**Reason:** `img-src 'self' data: https: http:` and `connect-src 'self' https: http: ws: wss:` allow broad sources. Tightening to specific domains would require knowing all external APIs, CDNs, and image hosts; risks breaking functionality.

### Dangerous JS Functions — Low (10110)

**Reason:** `eval()` in Next.js/turbopack chunks is from framework tooling, not app code. Mitigated by CSP.

### Insufficient Site Isolation Against Spectre — Low (90004)

**Status:** `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy` are set. Full Spectre mitigation may require `Cross-Origin-Embedder-Policy`, which can break cross-origin resources.

### Server Leaks Version — Low (10036)

**Status:** `server_tokens off` in nginx reduces to `Server: nginx`. Fully removing the header needs `ngx_headers_more` or similar.

### Timestamp Disclosure — Low (10096)

**Reason:** Unix timestamps in API/data responses. Generally acceptable; removing would require design changes.

---

## Round 1 Fixes (Original)

### Content Security Policy (CSP) Header — Medium (10038)

**Fix:** Added CSP in `frontend-nextjs/next.config.js` with `form-action`, `base-uri`, and other directives.

### Missing Anti-clickjacking Header — Medium (10020)

**Fix:** `X-Frame-Options: DENY` and `frame-ancestors 'none'` in CSP.

### Permissions Policy — Low (10063)

**Fix:** `Permissions-Policy` in Next.js and backend.

### Spectre Isolation — Low (90004)

**Fix:** `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy`.

### X-Powered-By Leak — Low (10037)

**Fix:** `poweredByHeader: false` and `proxy_hide_header X-Powered-By` in nginx.

### Server Version Leak — Low (10036)

**Fix:** `server_tokens off` in nginx configs.

## Deployment Steps

1. **Frontend:** Rebuild and redeploy Next.js (`npm run build` / Docker).
2. **Backend:** Redeploy backend (security middleware changes).
3. **Nginx:** Reload nginx after copying updated configs:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Re-run OWASP ZAP scan to verify fixes.
