# PaaS / Jump Server: Central + Separate DB Architecture

## Summary

- **Jump server (MSP/partner) has its own database** — no need to remove it.
- **Tenant-admins and MSPs** are created in **Resolvify central server**; central is source of truth for who they are. Licensing is checked **on the central server**.
- **Users** (name, node details, etc.) are created by MSP/tenant-admin in **their platform** (local DB on the jump server). Those user details are **synced to central for billing only**.
- This keeps the partner/MSP database separate while central has what it needs for licensing and billing.

---

## 1. Where things are created

| Entity | Created in | Synced / used where |
|--------|------------|----------------------|
| **Tenant-admins / MSPs** | **Central Resolvify** (super admin / your app) | Central is source of truth; edge either syncs these identities or validates login against central. |
| **Users** (name, node details, etc.) | **MSP / tenant-admin platform** (jump server, local DB) | **Synced to central for billing only.** |

So:
- You create MSPs/tenant-admins in central (dev or production Resolvify).
- MSP/tenant-admin creates end-users in their own platform (jump server); those user records stay in the partner DB and are synced to central for billing.

---

## 2. Licensing

- **Licensing is checked on the central server.**
- The jump server (or any edge) calls central to validate license/limits when needed (e.g. on login, or when checking seat/node limits). Central holds subscriptions and limits; edge enforces based on central’s response.

---

## 3. Sync flows (to implement / align)

1. **Central → Edge (optional, depending on auth design)**  
   - Edge needs to know which tenant-admins/MSPs exist so they can log in. Either:
     - Edge syncs tenant-admin/MSP identities from central into its DB (periodic or on-demand), or  
     - Edge validates login by calling central (“is this email/password a valid tenant-admin/MSP?”) and gets back identity + limits.

2. **Edge → Central (for billing)**  
   - When MSP/tenant-admin creates (or updates) **users** (name, node details, etc.) in their platform, the edge **syncs those user details to central** so central can use them for **billing**.  
   - Sync can be: on create/update, or batched (e.g. periodic). Central stores a copy for billing; source of truth for “user list” on the edge remains the edge DB.

---

## 4. Database layout

- **Central Resolvify:** Tenants (MSP/tenant-admin orgs), tenant-admin/MSP user accounts, subscriptions, license keys, limits, and **billing copy of user details** (synced from edges).
- **Jump server / MSP platform:** Separate DB with: local tenant context, **users** (name, node details) created by MSP/tenant-admin, and optionally a cached copy of tenant-admin/MSP identities if using sync-from-central.

---

## 5. Minimal changes to get there

- Keep **separate DB** on the jump server; no need to remove it.
- **Central:** Already has super admin to create tenants/MSPs and subscriptions; add or use an API so that:
  - Edge can **validate** tenant-admin/MSP login and get **license/limits** (or edge syncs these from central).
  - Edge can **push user details** (name, node details) to central for billing.
- **Edge (jump server):**  
  - When MSP/tenant-admin creates a user (name, node details), save in **local DB** and **sync that record to central** (billing).  
  - When license/limits are needed, **call central** to check (or use cached limits refreshed from central).

This way the database stays separate for the MSP/partner, and the central server has the info it needs for licensing and billing without changing everything at once.

---

**Implementation:** See **PAAS_IMPLEMENTATION_PLAN.md** for the concrete changes (config, central APIs, edge auth, user sync, and docs) to implement this step by step.
