# ManageEngine ServiceDesk Plus (and Zoho) OAuth Redirect URI

When you connect **ManageEngine ServiceDesk Plus** or **Zoho** to Resolvify, you must register a **Redirect URI** in the OAuth app. That URI is where the user is sent after authorizing the app. Resolvify’s backend handles the callback at:

**Path:** `/oauth/callback`  
**Full redirect URI:** `{BACKEND_BASE_URL}/oauth/callback`

Use the **backend** base URL (the host and port that serve the Resolvify API), not the frontend app URL.

---

## Resolvify SaaS (resolvify.tech)

- Backend is served on the same host (e.g. `https://resolvify.tech`) and `/oauth/callback` is proxied to the backend.
- **Redirect URI:** `https://resolvify.tech/oauth/callback`
- In ManageEngine (or Zoho): add exactly this URL as an allowed redirect URI for your OAuth client.
- Ensure your nginx (or reverse proxy) forwards **`/oauth/callback`** to the backend (port 8000), same as `/api/`.

---

## Resolvify PAAS (self‑hosted / on‑prem)

Use the URL that users and ManageEngine can reach when they are redirected after login.

- **If the backend is on its own host (e.g. API subdomain):**  
  `https://api.your-company.com/oauth/callback`  
  (or whatever your backend base URL is)

- **If the backend is on the same host as the app (e.g. combined deployment):**  
  `https://your-resolvify-host.com/oauth/callback`  
  (again, the host that serves the Resolvify backend and where `/oauth/callback` is routed)

- **If you use HTTP (e.g. internal only):**  
  `http://192.168.48.10:8000/oauth/callback`  
  (replace with your backend host and port). Many OAuth providers require **HTTPS** in production; use HTTP only for local/dev if allowed.

---

## Backend configuration

The backend uses:

- **Env:** `OAUTH_CALLBACK_URL` — default `http://localhost:8000/oauth/callback`
- For SaaS/PAAS, set this (or ensure the app uses the same value as in the UI) so it matches what you registered in ManageEngine:

  ```bash
  # SaaS
  OAUTH_CALLBACK_URL=https://resolvify.tech/oauth/callback

  # PAAS (example)
  OAUTH_CALLBACK_URL=https://your-resolvify-host.com/oauth/callback
  ```

If you don’t set it, the backend falls back to the default; the **exact** redirect URI stored in the connection (e.g. from the Add/Edit Connection form) must match what is registered in ManageEngine.

---

## Summary

| Deployment | Redirect URI to register |
|------------|---------------------------|
| **SaaS (resolvify.tech)** | `https://resolvify.tech/oauth/callback` |
| **PAAS (your host)** | `https://<your-backend-host>/oauth/callback` |
| **Local dev** | `http://localhost:8000/oauth/callback` |

Use the same value in:

1. ManageEngine (or Zoho) OAuth app → Redirect URI
2. Resolvify → Add/Edit Connection → Redirect URI field
3. (Optional) Backend env `OAUTH_CALLBACK_URL` so defaults are correct
