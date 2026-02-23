# PaaS Central Sync – Implementation Plan

This document lists the concrete changes needed to implement the architecture in **PAAS_CENTRAL_ARCHITECTURE.md**: tenant-admins/MSPs in central, users created on edge and synced to central for billing, licensing checked on central.

---

## Phase 1: Config and central API client (edge)

**Goal:** Edge (jump server) can be configured to talk to central and call one API.

### 1.1 Add config (central server URL, optional API key)

**File:** `backend/app/core/config.py`

- Add:
  - `CENTRAL_SERVER_URL: Optional[str] = None` (e.g. `https://dev.resolvify.tech` or `https://app.resolvify.tech`). When set, edge is “central-connected”.
  - `CENTRAL_API_KEY: Optional[str] = None` (optional; for authenticating edge → central calls).
- Read from env: `CENTRAL_SERVER_URL`, `CENTRAL_API_KEY`.

### 1.2 Central API client (edge)

**New file:** `backend/app/services/central_client.py`

- Module that:
  - Uses `settings.CENTRAL_SERVER_URL` and `settings.CENTRAL_API_KEY`.
  - Has functions (to be used in Phase 2 and 3):
    - `validate_paas_login(email: str, password: str) -> Optional[dict]`  
      Calls central; returns user + tenant + limits or None. (Central will expose this in Phase 2.)
    - `sync_users_for_billing(tenant_id: int, users: list[dict]) -> bool`  
      POSTs user list to central for billing. (Central will expose this in Phase 3.)
- Use `httpx` (or `requests`) with timeout; handle connection errors and non-2xx; log failures. No auth to central until we add CENTRAL_API_KEY to the central endpoint (optional later).

**Dependencies:** `httpx` is likely already in requirements; if not, add it.

---

## Phase 2: Central – PaaS auth/validate and license check

**Goal:** Central exposes an API that the edge can call to validate tenant-admin/MSP login and get limits (so licensing is checked on central).

### 2.1 Central: PaaS validate-login endpoint

**New file (central only):** `backend/app/api/v1/endpoints/paas_auth.py`

- **POST /api/v1/paas/validate-login**  
  - Body: `{ "username": "email", "password": "..." }`.  
  - Logic: Same as existing login – use `authenticate_user(db, username, password)`. If valid, ensure the user is a tenant_admin or msp_admin (or admin with tenant); if not, return 403.  
  - Response: 200 + JSON with user id, email, full_name, role, tenant_id, tenant (name, is_msp), and **limits** (e.g. max_seats, max_nodes from subscription for that tenant). If no subscription, return defaults or zeros.  
  - Security: This endpoint must be protected (e.g. only callable by edge: API key in header, or IP allowlist later). For now, require a header like `X-Paas-API-Key` and check it against a new setting `PAAS_EDGE_API_KEY` on central (so only your edges can call it).  
- Register router in `backend/app/api/v1/api.py` under prefix `/paas` (or similar).

**Central config:** Add `PAAS_EDGE_API_KEY: Optional[str] = None` in `config.py`. Edge will send this in `X-Paas-API-Key` when calling central.

### 2.2 Edge: Use central for tenant-admin/MSP login when configured

**File:** `backend/app/api/v1/endpoints/auth.py` (login endpoint)

- Before calling local `authenticate_user`:
  - If `settings.DEPLOYMENT_MODE == "paas"` and `settings.CENTRAL_SERVER_URL`:
    - First try `central_client.validate_paas_login(form_data.username, form_data.password)`.
    - If central returns 200 and body has user + tenant + limits:
      - Option A (simplest): Create or update a **local** user record for this tenant-admin/MSP (sync from central) so that existing auth/me and JWT flow still work; issue JWT from edge as today. Store limits in session or in a small “paas_limits” cache keyed by user/tenant.
      - Option B: Don’t store user locally; have central return a signed token that the edge trusts. That’s a bigger change; Option A is minimal.
    - If central returns 401/403 or unreachable: either fail login (“Could not validate with central”) or fall back to local DB (configurable) for resilience.
  - If not paas or no CENTRAL_SERVER_URL: keep current behavior (local `authenticate_user` only).

**File:** `backend/app/services/central_client.py`

- Implement `validate_paas_login`: POST to `{CENTRAL_SERVER_URL}/api/v1/paas/validate-login` with username/password; add header `X-Paas-API-Key: {CENTRAL_API_KEY}` if set. Parse response and return the dict (user + tenant + limits) or None.

**Edge config (standalone compose / .env):** Set `DEPLOYMENT_MODE=paas`, `CENTRAL_SERVER_URL=https://dev.resolvify.tech` (or prod), and `CENTRAL_API_KEY=<key>` (same as central’s `PAAS_EDGE_API_KEY`).

---

## Phase 3: Central – Receive user sync for billing

**Goal:** When MSP/tenant-admin creates (or updates) a user on the edge, edge sends that user’s details to central for billing.

### 3.1 Central: Billing sync endpoint and storage

**New table (central):** e.g. `paas_synced_users` or reuse/extend existing structure.

- Fields (minimal): central tenant_id, edge_user_id (or email), email, full_name, node_details (JSON or text), synced_at, source (e.g. "paas_edge"). So central has a copy of “user records from edges” for billing.

**New file (central):** `backend/app/api/v1/endpoints/paas_billing.py`

- **POST /api/v1/paas/billing/sync-users**  
  - Body: `{ "tenant_id": 123, "users": [ { "id", "email", "full_name", "role", "tenant_id", "node_details" or similar } ] }`.  
  - Auth: Require `X-Paas-API-Key` (same as Phase 2).  
  - Logic: Upsert into `paas_synced_users` (or equivalent) by tenant_id + user id/email; update synced_at.  
- Register in `api.py`.

**SQL migration (central):** Create table `paas_synced_users` (or add columns to an existing billing-related table if you prefer).

### 3.2 Edge: Sync users to central when created/updated

**Files where users are created/updated by MSP or tenant-admin:**

- `backend/app/api/v1/endpoints/tenant_admin.py`: `create_customer_user`, `update_customer_user` (and delete if exists).
- `backend/app/api/v1/endpoints/client_admin.py`: `create_tenant_user`, update user.
- Any other “create user” path under tenant-admin or MSP.

**Change:** After successfully creating or updating a user (and committing to local DB), call `central_client.sync_users_for_billing(tenant_id, [user_payload])`. Payload = minimal fields needed for billing (id, email, full_name, role, tenant_id, node details if any). Fire-and-forget or background task so that API response is not blocked; log errors.

**File:** `backend/app/services/central_client.py`

- Implement `sync_users_for_billing(tenant_id, users)`:
  - POST to `{CENTRAL_SERVER_URL}/api/v1/paas/billing/sync-users` with body `{ "tenant_id": tenant_id, "users": users }`.
  - Add `X-Paas-API-Key` if configured.
  - Return True on 2xx, False otherwise; log on failure.

---

## Phase 4: License/limits enforcement on edge (using central data)

**Goal:** Edge enforces seat/node limits that come from central (from validate-login response or a separate “get limits” call).

### 4.1 Use limits from central on edge

- When edge gets back limits from `validate_paas_login` (Phase 2), cache them (e.g. in memory keyed by tenant_id, or in DB). When checking “can I add another user?” or “can I add another node?”, use cached limits; if missing or stale, optionally call central again (e.g. GET /api/v1/paas/tenant/{id}/limits) or re-validate on next login.
- **File:** `backend/app/services/subscription/subscription_tracker.py` (or equivalent)  
  - If `DEPLOYMENT_MODE=paas` and `CENTRAL_SERVER_URL` is set, prefer limits from central (cached or fetched). If central is unreachable, either deny or use a local default (configurable).

### 4.2 (Optional) Central: GET limits endpoint

- **GET /api/v1/paas/tenants/{tenant_id}/limits**  
  - Returns max_seats, max_nodes, etc. for that tenant (from subscription). Protected by `X-Paas-API-Key`.  
  - Edge can call this when it needs to re-check limits without re-login.

---

## Phase 5: Standalone / docker-compose and docs

### 5.1 Standalone compose and .env

- **File:** `docker-compose.standalone.yml` (or env example)
  - Add env vars for edge: `CENTRAL_SERVER_URL`, `CENTRAL_API_KEY`, `DEPLOYMENT_MODE=paas`. Document that if these are set, tenant-admin/MSP login is validated against central and user sync runs to central for billing.

### 5.2 Docs

- **RUN_STANDALONE.md:** Add a short “Central-connected mode” section: set CENTRAL_SERVER_URL and CENTRAL_API_KEY; then tenant-admins/MSPs are validated via central and user changes are synced for billing. Link to PAAS_CENTRAL_ARCHITECTURE.md and this plan.
- **PAAS_CENTRAL_ARCHITECTURE.md:** Add a one-line reference: “See PAAS_IMPLEMENTATION_PLAN.md for the concrete implementation steps.”

---

## Order of work (summary)

1. **Phase 1:** Config + `central_client.py` (stubs for validate_paas_login and sync_users_for_billing).
2. **Phase 2:** Central: `paas_auth.py` (validate-login) + central config PAAS_EDGE_API_KEY. Edge: auth.py login calls central when paas + CENTRAL_SERVER_URL set; implement `validate_paas_login` in central_client.
3. **Phase 3:** Central: table + `paas_billing.py` (sync-users). Edge: after create/update user in tenant_admin (and client_admin), call `sync_users_for_billing`.
4. **Phase 4:** Edge uses limits from central (cached from login or GET limits). Optional: central GET limits endpoint.
5. **Phase 5:** Compose/env and docs.

This keeps the edge DB separate, central as source of truth for tenant-admins/MSPs and licensing, and user data created on the edge synced to central for billing with minimal change to existing flows.
