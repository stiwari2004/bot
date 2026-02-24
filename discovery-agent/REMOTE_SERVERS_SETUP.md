# Remote Servers Discovery Setup Guide

## Deploying the app (backend + frontend + discovery)

For the server that runs the Resolvify API (e.g. PAAS at `http://192.168.48.10:8000`), build and run the **complete app image**. That image includes the discovery-agent folder so `/api/v1/tenant-admin/discovery/run`, `agent.tar.gz`, and `agent.zip` work.

**Build the complete app image (from repo root):**
```bash
# From repo root (directory that contains backend/, frontend-nextjs/, discovery-agent/):
docker build -f Dockerfile.combined -t resolvify-app:latest .

# Or use the script:
./build-app.sh
```

**Run the app (backend serves API + static frontend; discovery endpoints included):**
```bash
docker run -p 8000:8000 -e DATABASE_URL=... resolvify-app:latest
```

Then one-step discovery works: `curl -sSL "http://YOUR_HOST:8000/api/v1/tenant-admin/discovery/run" -o run.py && python3 run.py "http://YOUR_HOST:8000/api/v1/tenant-admin/discovery/ingest" "TOKEN"`.

---

## Network Discovery (Recommended)

When `network_discovery.enabled: true` (or `DISCOVERY_AUTO_SCAN=1`), the agent:

1. **Phase 1: Ping sweep** – Uses the jump server's subnet (e.g. /24) to find all alive hosts. Port-agnostic; finds anything that responds to ping.
2. **Phase 2: Fingerprint** – Probes common ports (22, 5985, 5432, etc.) to get hostname and OS.
3. **Phase 3: Full scan** – Runs full inventory (CPU, memory, disk) on Linux/Windows/DBs via SSH/WinRM/SNMP.

Run `python3 discover.py "INGEST_URL" "TOKEN"` on the jump server. No pre-configured server list required.

---

## Discovery agent Docker image (scanner only)

For running the **scanner** in a container (e.g. on a jump server), build the **discovery-agent-only** image. This is separate from the app image above: the app image runs the API (and serves run/agent.tar.gz/agent.zip); the agent image only runs discovery and posts to the ingest URL.

**Build the agent image (optional; only if you run discovery inside Docker):**
```bash
# From repo root:
docker build -f discovery-agent/Dockerfile -t resolvify-discovery-agent discovery-agent

# Or from discovery-agent directory:
cd discovery-agent && docker build -t resolvify-discovery-agent .
```

**Run (customer passes ingest URL and token via env):**
```bash
docker run --rm \
  -e DISCOVERY_INGEST_URL=https://your-app.example.com/api/v1/tenant-admin/discovery/ingest \
  -e DISCOVERY_TOKEN=YOUR_TOKEN \
  resolvify-discovery-agent
```

**Run from a jump server (network discovery):** So the container can ping and reach the same network as the host, use host network on Linux:
```bash
docker run --rm --network host \
  -e DISCOVERY_INGEST_URL=https://.../ingest \
  -e DISCOVERY_TOKEN=YOUR_TOKEN \
  resolvify-discovery-agent
```
On Windows/macOS use port publishing and ensure the container can reach the target subnet; for full ping sweep from a jump server, running the agent directly on the host (bootstrap or discover.py) may be simpler.

**Optional:** Mount a custom `config.yaml` for remote_servers/network/storage:
```bash
docker run --rm -v /path/to/config.yaml:/app/config.yaml -e DISCOVERY_INGEST_URL=... -e DISCOVERY_TOKEN=... resolvify-discovery-agent
```
Mount SSH keys if needed: `-v ~/.ssh:/root/.ssh:ro` (adjust user as needed).

---

## Production one-command install (bootstrap)

For **controlled environments** (e.g. your own jump server) where you don’t use the Docker image: use the bootstrap script so the agent is downloaded, dependencies installed (venv), and discovery run in one go.

**Linux / macOS (bash):**
```bash
# With script from repo (after copying bootstrap.sh to the server):
bash bootstrap.sh "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"

# Or one-liner if your app serves the script (replace URL with your Resolvify base):
curl -sSL "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/bootstrap.sh" | bash -s -- "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```
Installs to `~/.resolvify-discovery` (or `$RESOLVIFY_DISCOVERY_DIR`). Requires: `curl`, `unzip`, `python3`.

**Windows (PowerShell):**
```powershell
# After copying bootstrap.ps1 to the server (or downloading it):
.\bootstrap.ps1 -IngestUrl "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" -Token "YOUR_TOKEN"
```
Installs to `%USERPROFILE%\.resolvify-discovery` (or `$env:RESOLVIFY_DISCOVERY_DIR`). Requires: PowerShell 5+, Python in PATH.

If the server cannot download `agent.zip` (e.g. Docker returns HTML), the script tells you to copy the `discovery-agent` folder manually and run `python3 discover.py "INGEST_URL" "TOKEN"` (see Legacy: Manual Server List below).

---

## Legacy: Manual Server List

## Problem
When running discovery from a jump server, it only reports the jump server itself, not the other servers accessible via SSH.

## Solution (manual config)

### Step 1: Get the Discovery Script

**⚠️ IMPORTANT**: The zip endpoint may not work in Docker. Use **Option B (Manual Setup)** instead.

**Option A: Direct Download (may not work in Docker)**
```bash
curl -sSL "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/run" -o run.py
python3 run.py "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```

**Option B: Manual Setup (RECOMMENDED)**

**Copy discovery-agent folder to jump server:**

From your local machine (where you have the bot repo):
```bash
# Linux/Mac:
scp -r discovery-agent/ labadmin@jump01:~/

# Windows (PowerShell with OpenSSH):
scp -r discovery-agent\ labadmin@jump01:~/

# Or use WinSCP/FileZilla GUI to copy the folder
```

**Then on jump server (one command, no sudo pip):**
```bash
cd ~/discovery-agent
python3 discover.py "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```
`discover.py` creates a virtual environment (`.venv`), installs dependencies, and runs discovery. Use this on Debian/Ubuntu where `pip3 install` is blocked (externally-managed-environment). It also auto-discovers servers from `/etc/hosts` and `~/.ssh/known_hosts`.

**Option C: Download agent.zip (if endpoint works)**

```bash
curl -sSL "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/agent.zip" -o agent.zip

# Verify it's a valid zip (not HTML error page):
file agent.zip
# Should show: "Zip archive data"
# If it shows "HTML document", the endpoint failed - use Option B instead

# If valid:
unzip agent.zip
cd discovery-agent
python3 discover.py "https://.../ingest" "YOUR_TOKEN"
```

### Step 2: Configure and run (no separate pip step)

On Debian/Ubuntu do **not** run `sudo pip3 install` (it will fail). Use the `discover.py` script:

```bash
cd ~/discovery-agent
python3 discover.py "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```

With a config file (e.g. after editing `config.yaml` for remote_servers):
```bash
python3 discover.py
```

**Note:** `discover.py` automatically discovers servers from `/etc/hosts` and `~/.ssh/known_hosts` when run on a jump server, so you may not need to configure `remote_servers.servers` manually.

### Step 3: Create/Edit config.yaml

The script generates a basic `config.yaml`, but you need to **enable and configure remote_servers**:

```yaml
ingest:
  url: "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest"
  token: "YOUR_TOKEN"
  run_id: null

agent:
  enabled: true  # Reports the jump server itself

# Remote servers: discover other servers from jump server
remote_servers:
  enabled: true   # ← CHANGE THIS TO true
  timeout: 30
  # If running ON the jump server, omit jump_server section
  # If running FROM another machine, configure jump_server:
  # jump_server:
  #   host: "jump.example.com"
  #   username: "admin"
  #   password: "secret"
  servers:
    # Add your servers here:
    - host: "192.168.1.10"  # Linux server 1
      os_type: "linux"
      username: "ubuntu"
      password: "secret"
      port: 22
    - host: "192.168.1.11"  # Linux server 2
      os_type: "linux"
      username: "root"
      use_keys: true
      key_file: "/home/user/.ssh/id_rsa"
    - host: "192.168.1.12"  # Monitoring server
      os_type: "linux"
      username: "admin"
      password: "secret"
    - host: "192.168.1.20"  # Windows server (if any)
      os_type: "windows"
      username: "Administrator"
      password: "secret"
      port: 5985
    - host: "192.168.1.30"  # Database server
      db_type: "postgresql"
      username: "postgres"
      password: "secret"
      db_port: 5432
```

### Step 4: Run Discovery

```bash
python3 run.py config.yaml
```

Or if using the one-step script:
```bash
python3 run.py
```

### Step 5: Verify Results

Check the Resolvify UI → Tenant Admin → Discovery → Assets to see all discovered servers.

## Troubleshooting

### Issue: 404 on `/api/v1/tenant-admin/discovery/run`

**Solution**: Use manual setup (Option B above) or download agent.zip directly.

### Issue: 404 on `agent.tar.gz` or `agent.zip` (“Tar download failed … trying zip … Download failed … reporting this host only”)

**Cause**: The backend container cannot find the `discovery-agent` folder, so it returns 404 for both archive endpoints.

**Solution** (when using Docker Compose from the repo):

- Ensure the backend service mounts the discovery-agent folder. In your compose file, add to the backend `volumes`:
  ```yaml
  - ./discovery-agent:/app/discovery-agent
  ```
- Restart the backend container so the mount is applied.

**Solution** (when running the backend in Docker without compose):

- Mount the repo’s discovery-agent directory into the container, e.g.:
  ```bash
  docker run ... -v /path/to/repo/discovery-agent:/app/discovery-agent ...
  ```
- Or set `DISCOVERY_AGENT_DIR=/path/inside/container/to/discovery-agent` and ensure that path exists in the image or is mounted.

**Solution** (PAAS or pre-built backend image where dev/prod work but this server returns 404):

- **Recommended:** Build and deploy the **complete app image** so the API and discovery endpoints all work:
  ```bash
  # From repo root
  docker build -f Dockerfile.combined -t resolvify-app:latest .
  # Then run resolvify-app:latest on PAAS (port 8000).
  ```
  Or run `./build-app.sh` from repo root.
- If you only need the backend (no frontend in image), build the backend from repo root: `docker build -f backend/Dockerfile -t your-backend .`
- Alternatively, mount discovery-agent into the container or set `DISCOVERY_AGENT_DIR` to a path where you’ve placed the folder.

### Issue: "remote_servers scanner not available"

**Solution**: Install dependencies:
```bash
pip3 install paramiko pywinrm
```

### Issue: "Connection refused" or "Authentication failed"

**Solution**: 
1. Test SSH manually: `ssh user@server` from jump server
2. Verify credentials in config.yaml
3. Check if servers are accessible from jump server
4. For Windows: Ensure WinRM is enabled and accessible

### Issue: Only jump server reported

**Solution**: 
1. Check `config.yaml` has `remote_servers.enabled: true`
2. Verify `remote_servers.servers` list is not empty
3. Check error messages in output for connection failures

## Quick Test

Test SSH connectivity from jump server first:
```bash
# Test SSH to each server
ssh user@192.168.1.10 "hostname"
ssh user@192.168.1.11 "hostname"
# etc.
```

If SSH works manually, discovery should work too.
