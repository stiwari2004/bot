# Running Resolvify from the pre-built image (e.g. on jump server)

Use this when you have only the saved image (`resolvify-app.tar`) and want to run the app **without the full repo**. Your source code never goes to the client machine.

## Architecture (PaaS / central)

The jump server has **its own database**. The intended model (see **PAAS_CENTRAL_ARCHITECTURE.md** for full detail):

- **Tenant-admins / MSPs** are created in **Resolvify central** (dev or production); central is source of truth for them. **Licensing is checked on the central server.**
- **Users** (name, node details) are created by MSP/tenant-admin in **their platform** (this jump server’s DB) and **synced to central for billing only.**

So: separate DB on the edge; central has MSP/tenant-admin identities and licensing; user details created on the edge are synced to central for billing. Until central sync and license-check integration are fully in place, the seed step below is a temporary way to bootstrap local accounts.

## Your code stays private

- **On your machine (where the repo lives):** You build the Docker image and save it to a `.tar` file. You also copy only **three files** to the client: the `.tar`, the compose file, and the init SQL.
- **On the client/jump server:** The client has **only** Docker, the image (loaded from the tar), `docker-compose.standalone.yml`, `init-pgvector.sql`, and a `.env` you create (keys and passwords). **No repository, no source code, no copy of your codebase** — only the built image and the minimal config needed to run it.

## What you need on the server

1. **Docker** and **Docker Compose** (v2).
2. **Loaded image:** `resolvify-app:latest` (from `docker load -i resolvify-app.tar`).
3. **Three things** in one directory:
   - `docker-compose.standalone.yml`
   - `init-pgvector.sql`
   - **`.env`** (required) with at least `CREDENTIAL_ENCRYPTION_KEY` — see below.

**Important:** The app listens on port **8000** (not 3000 or 8080). Use `-p 8000:8000` if you run the container by hand.

## 0. Build and ship the image (on your machine only)

Do this where your repo lives. The client never sees the repo.

```bash
# In your repo root (on your dev/build machine)
docker build -f Dockerfile.combined -t resolvify-app:latest .
docker save resolvify-app:latest -o resolvify-app.tar
```

Copy **only these** to the client (e.g. via SCP, USB, or your delivery process):

- `resolvify-app.tar`
- `docker-compose.standalone.yml`
- `init-pgvector.sql`

Do **not** copy the repo, backend, or frontend source. The client only needs the image and the two config files above (plus a `.env` they create on the server).

## 1. Create a directory and copy files (on the client)

The folder name is up to you; it doesn't have to be `resolvify`. Example:

```bash
mkdir -p ~/resolvify
cd ~/resolvify
```

Put the files you received (no repo) into this directory:

- `resolvify-app.tar`
- `docker-compose.standalone.yml`
- `init-pgvector.sql`

## 2. Create the required `.env` file

The app **will not start** without `CREDENTIAL_ENCRYPTION_KEY`. Create a `.env` file in the **same directory** as the compose file.

**Generate a key** (on any machine with Python):

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

You'll get a long string (e.g. `xYz123...`). Then create `~/resolvify/.env` (or your directory) with:

```env
CREDENTIAL_ENCRYPTION_KEY=paste_the_generated_key_here
SECRET_KEY=your-secret-key-at-least-32-characters-long
POSTGRES_PASSWORD=password
```

Use the same key you generated for `CREDENTIAL_ENCRYPTION_KEY`; change `SECRET_KEY` and `POSTGRES_PASSWORD` to your own values.

**Do not set `DATABASE_URL` in `.env`.** The compose file sets it. With the current standalone compose, `.env` is only used by Compose for variable substitution (on the host); it is not loaded into the app container, so a stray `DATABASE_URL` in `.env` will no longer override the correct URL.

## 3. Load the image and start

```bash
cd ~/resolvify   # or wherever you put the files

# Load the image (if not already done)
docker load -i resolvify-app.tar

# Start all containers (Postgres, Redis, app, worker)
docker compose -f docker-compose.standalone.yml up -d

# Check they are running
docker compose -f docker-compose.standalone.yml ps
```

If you previously ran the app container by hand (e.g. `docker run ... resolvify-app`), remove it first so the compose stack can create its own:

```bash
docker rm -f resolvify-app
```

Then run the `docker compose` command again.

## 4. Seed initial accounts (first-time setup)

**Do I create the login ID in the super admin section of dev or production resolvify.tech?**  
No. The jump server has **its own database**. It is not connected to dev.resolvify.tech or production resolvify.tech. Users and tenants you create in super admin on dev or production exist only in that environment. To log in on the **jump server**, you must create the accounts **on the jump server itself** (using the seed command below).

The standalone database starts empty. To create **tenant admin** and **user** accounts (and optionally a vendor super admin), run the seed script **inside the app container on the jump server** (no repo needed — the script is in the image):

```bash
# Replace with your desired admin email and password
docker exec resolvify-app python scripts/seed_dev_data.py admin@yourcompany.com 'YourSecurePassword'
```

This creates:

- **Tenant** (default) and a **tenant admin** user with the email/password you passed — customers log in at the **main login** (`/`) or at **Tenant Admin / MSP Login** (`/tenant-admin/login`).
- A **regular user** `dev@dev.resolvify.tech` with the same password — for testing.
- **Super admin** (vendor only) — not shown on the customer login page; only the vendor uses `/super-admin/login` (direct URL) with the same email/password for platform administration.

**Customer-facing login:** At `http://<server>:8000` customers see only **Sign In** (user/tenant admin) and **Tenant Admin / MSP Login**. No demo mode and no super admin link. License checks run after login where applicable.

## Access the app in the browser

- **URL:** `http://<jump-server-IP>:8000`
- Replace `<jump-server-IP>` with the actual IP or hostname (e.g. `http://192.168.1.10:8000` or `http://jump01:8000`).

All services (API + frontend) are served from the **app** container on port **8000**. You don't need to open other "containers" in the browser—just that URL.

## Optional: more environment variables

You can add these to `.env` if you need them:

```env
ENABLE_TICKETING_POLLER=true
GEMINI_API_KEY=...
```

The compose file already loads `.env` for the app and worker.

## Troubleshooting

### "could not translate host name ... to address" / "Name or service not known"

The app is using a wrong `DATABASE_URL`. **Fix:** Update to the latest `docker-compose.standalone.yml` from the repo (it no longer passes `.env` into the app container, so the compose-set `DATABASE_URL` is always used). Ensure your `.env` has `POSTGRES_PASSWORD=password` (or your chosen password) so the URL is built correctly. Then:

```bash
docker compose -f docker-compose.standalone.yml down
docker compose -f docker-compose.standalone.yml up -d
```

### "password authentication failed for user \"postgres\""

Postgres was already initialized (the data volume already exists) with a **different** password than the one in your current `.env`. Either:

**Option A – Use the same password as when the volume was first created**  
Set `POSTGRES_PASSWORD` in `.env` to whatever password was used the first time you ran the stack (e.g. if you had `POSTGRES_PASSWORD=something` before, use that again).

**Option B – Start with a fresh database (recommended if you don’t need the old data)**  
Remove the volumes so Postgres is re-initialized with the password from your current `.env`:

```bash
docker compose -f docker-compose.standalone.yml down -v
# Ensure .env has: POSTGRES_PASSWORD=password  (or your chosen password)
docker compose -f docker-compose.standalone.yml up -d
```

After this, the app and Postgres will both use the password from `.env`.

### Stuck on "Loading..." or "Connecting"

The UI may hang if the browser cannot reach the API (CORS, wrong host, or bad/stale token), or if **CSP blocks the app’s scripts**.

1. **Ensure the app container has `ENVIRONMENT=development`** (the default in `docker-compose.standalone.yml`). This allows CORS from any origin (e.g. `http://<jump-server-ip>:8000`) so the frontend’s API calls succeed.
2. **Open the app at the same host you use in the browser** — e.g. `http://<jump-server-ip>:8000` or `http://jump01:8000`. Don’t mix hostnames (e.g. IP vs hostname) if your DNS differs.
3. **Open in a private/incognito window** or **clear site data** (DevTools → Application → Storage → Clear site data) to remove a bad cached token.
4. **Check the browser console** (F12 → Console): look for failed requests to `/api/v1/auth/me` or CORS errors. If you see CORS or network errors, rebuild the image so the backend has the latest CORS fix (dev/standalone allows any origin via regex).
5. The frontend times out the auth check after 15 seconds; you should then see the login page or an error instead of spinning forever.

### Console: "Executing inline script violates... Content Security Policy"

If the console shows CSP errors like `script-src 'self'` blocking inline scripts, the **page HTML is being served with a CSP that blocks the Next.js app’s inline scripts**, so the app never runs and stays on "Loading". **Fix:** Rebuild the image from a repo that has the security middleware fix: the backend uses a **relaxed CSP for SPA routes** (allows `'unsafe-inline'` for script and style only on frontend paths, not on `/api`). Rebuild, save a new `resolvify-app.tar`, and redeploy on the client (see section 0).

### License code

You are **not** required to enter a license to use the app. License activation is only used in certain PaaS/super-admin flows. For the standalone deployment customers log in (main or Tenant Admin / MSP) and use the platform; no license prompt is needed.

### "CREDENTIAL_ENCRYPTION_KEY must be set"

Add `CREDENTIAL_ENCRYPTION_KEY=...` to `.env` (generate with the `python3 -c "from cryptography.fernet..."` command in section 2).

### Warnings about `version` being obsolete

You can remove the line `version: '3.8'` from the top of `docker-compose.standalone.yml`; modern Compose ignores it. The repo version may already have it removed.

## Useful commands

| Command | Purpose |
|--------|---------|
| `docker compose -f docker-compose.standalone.yml ps` | List running containers |
| `docker compose -f docker-compose.standalone.yml logs -f app` | Follow app logs |
| `docker compose -f docker-compose.standalone.yml down` | Stop and remove containers (data in volumes is kept) |
| `docker compose -f docker-compose.standalone.yml down -v` | Stop and remove containers and volumes (fresh DB next time) |

## Containers started

| Container        | Role                          | Port (host) |
|-----------------|-------------------------------|-------------|
| resolvify-postgres | PostgreSQL + pgvector       | 5432        |
| resolvify-redis    | Redis                        | 6379        |
| resolvify-app      | API + frontend (use this in browser) | **8000** |
| resolvify-worker   | Background worker            | —           |

You only need to open **http://&lt;server&gt;:8000** in the browser to use the app.
