# Running Resolvify from the pre-built image (e.g. on jump server)

Use this when you have only the saved image (`resolvify-app.tar`) and want to run the app without the full repo.

## What you need on the server

1. **Docker** and **Docker Compose** (v2).
2. **Loaded image:** `resolvify-app:latest` (from `docker load -i resolvify-app.tar`).
3. **Three things** in one directory:
   - `docker-compose.standalone.yml`
   - `init-pgvector.sql`
   - **`.env`** (required) with at least `CREDENTIAL_ENCRYPTION_KEY` — see below.

**Important:** The app listens on port **8000** (not 3000 or 8080). Use `-p 8000:8000` if you run the container by hand.

## 1. Create a directory and copy files

The folder name is up to you; it doesn't have to be `resolvify`. Example:

```bash
mkdir -p ~/resolvify
cd ~/resolvify
```

Copy from your dev machine (or repo) into this directory:

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

### Stuck on "Loading..." or loading loop

The UI may hang if the browser cannot reach the API or has a bad/stale token.

1. **Open the app in a private/incognito window** (no cached token).
2. **Or clear site data** for the app URL: DevTools → Application → Storage → Clear site data.
3. **Use "Skip login"** if you see a login screen: use the link/button to continue as guest so you can use the tool without an account.
4. **Check the browser console** (F12 → Console): look for failed requests to `/api/v1/auth/me` or CORS errors. Ensure you open the app at `http://<server-ip>:8000` (same host as the API).
5. After a code update, the frontend now times out the auth check after 15 seconds so loading should not spin forever; you should see the login page or an error.

### License code

You are **not** required to enter a license to use the app. License activation is only used in certain PaaS/super-admin flows. For the standalone deployment you can log in (or skip login) and use the platform; no license prompt is needed.

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
