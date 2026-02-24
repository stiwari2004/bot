# Production vs Standalone – keep them separate

## Roles

| Stack | Role | Who logs in here | Database |
|-------|------|------------------|----------|
| **Production** (`docker-compose.production.yml`) | **Central** (main Resolvify server) | Super admins, tenant-admins, MSPs, regular users – all must exist in **this** DB | Its own Postgres: `troubleshooting_ai` on `bot-prod-postgres` |
| **Standalone** (`docker-compose.standalone.yml`) | **PaaS edge** (jump server for MSP/tenant) | MSP/tenant admins – login is **validated by central**; users can be created locally and synced to central for billing | Its own Postgres: `troubleshooting_ai` on `resolvify-postgres` (different host/volume) |

So: **Production = central. Standalone = edge.** They must not share identity or DB.

## Why “production” might feel like “logging into central”

If the **production** backend has in its environment:

- `DEPLOYMENT_MODE=paas`
- `CENTRAL_SERVER_URL=https://...`

then production is acting as a **PaaS edge**: it will call that central URL to validate logins. So when you open the production UI and log in, you are “logging into central” (credentials checked on central). If central doesn’t have that user, or the request fails, you get 401.

**For production to be the central server (normal Resolvify server):**

- **Do not set** `DEPLOYMENT_MODE=paas` on production (or leave it unset / `saas`).
- **Do not set** `CENTRAL_SERVER_URL` on production.
- Then production uses **local auth only**: users (including `admin@resolvify.tech`) must exist in the **production** database.

**For standalone (jump server) to be the edge:**

- **Do set** on the standalone server: `DEPLOYMENT_MODE=paas` and `CENTRAL_SERVER_URL=<production URL>` (and `CENTRAL_API_KEY` if central requires it).
- Then standalone validates logins against production (central); MSP/tenant admins must exist on central.

## Why standalone login might not work

Login on the **standalone** (edge) is validated by **central**. The identity that can log in from the standalone must exist on **central** as a **User** (in the **users** table), not only as a tenant or super admin.

| What you created on production | Can they log in from standalone? |
|--------------------------------|----------------------------------|
| Tenant with `deployment_type=paas` only | **No** – no user to validate |
| **User** (in **users** table) with role **tenant_admin** or **msp_admin**, under that tenant | **Yes** – edge calls central validate-login with that email/password |
| Super admin only | **No** – PaaS validate-login checks **users** table, not super_admins |

**Checklist for standalone login:**

1. **On central (production):** Create a **User** (e.g. via Super Admin → Tenants → select tenant → add user, or Client Admin) with **email** and **password** and **role = tenant_admin** (or msp_admin for MSP). That user’s **tenant** can be `deployment_type=paas` or `saas`; the role is what matters for login.
2. **On standalone (edge):** In `.env` (or the env used by the app), set:
   - `DEPLOYMENT_MODE=paas`
   - `CENTRAL_SERVER_URL=https://<production-backend-url>` (no trailing slash)
   - `CENTRAL_API_KEY=<same as central’s PAAS_EDGE_API_KEY>` (if central requires it)
3. **From the standalone UI:** Open the main login page (e.g. `http://<standalone-ip>:8000/`) and sign in with that **user’s** email and password. The edge will call central to validate; on success it creates/updates a local user and issues a token.

If login still fails: confirm the user exists in **users** on central (`SELECT id, email, role, tenant_id FROM users WHERE email = '...';`), that the password is correct (or reset it on central), and that the standalone can reach `CENTRAL_SERVER_URL` (e.g. curl from the standalone host).

## Databases and data loss

- **Production** and **standalone** both use a DB named `troubleshooting_ai`, but they should run on **different hosts** (or at least different Docker projects/volumes). If you run both on the same host from the same directory, Compose project name is the same and **volumes can collide** (e.g. `postgres_data`), so one stack can overwrite the other’s data.
- To avoid that: run production and standalone on **different machines**, or use different Compose project names and distinct volume names so they never share a Postgres data volume.

## Check what’s in the production DB (read-only)

From the host where production is running:

```bash
# From repo root (adjust path if needed)
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f - < backend/sql/check_prod_db.sql
```

This prints:

- Super admin IDs and emails
- Tenant IDs and names
- User list (first 50) and row counts for main tables

Use this to confirm whether `admin@resolvify.tech` (or any user) and tenants/super_admins exist in **production** before changing env or compose.
