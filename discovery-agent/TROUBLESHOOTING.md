# Discovery Agent Troubleshooting

## Issue: "externally-managed-environment" when running pip

### Symptoms
```bash
$ sudo pip3 install -r requirements.txt
error: externally-managed-environment
× This environment is externally managed
```

### Solution

Do **not** use `sudo pip3 install`. Use the **`discover.py`** script instead—it creates a virtual environment (`.venv`) and installs dependencies there:

```bash
cd ~/discovery-agent
python3 discover.py "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```

Or with an existing config: `python3 discover.py`

---

## Issue: agent.zip is not a valid zip file

### Symptoms
```bash
$ curl -sSL "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/agent.zip" -o agent.zip
$ unzip agent.zip
unzip: cannot find zipfile directory
```

### Diagnosis

Check what you actually downloaded:
```bash
file agent.zip
# If it says "HTML document" or "empty", the endpoint returned an error page
# If it says "Zip archive data", the zip is corrupted

# Check first few bytes:
head -c 100 agent.zip
# If you see "<html>" or "<!DOCTYPE", it's an error page
```

### Solution: Manual Setup (Recommended)

Since the zip endpoint may not work in Docker, **copy the discovery-agent folder directly**:

**From your local machine (Windows):**
```powershell
# Using SCP (if you have OpenSSH):
scp -r discovery-agent/ labadmin@jump01:~/

# Or using WinSCP / FileZilla GUI
# Copy the entire discovery-agent folder to ~/ on jump server
```

**From your local machine (Linux/Mac):**
```bash
scp -r discovery-agent/ labadmin@jump01:~/
```

**Then on jump server (one command; no sudo pip):**
```bash
cd ~/discovery-agent
python3 discover.py "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
```
To use a config file (e.g. after enabling remote_servers in config.yaml): run `python3 discover.py` with no arguments.

### Alternative: Git Clone (if repo is accessible)

If the repo is on GitHub/GitLab:
```bash
git clone <repo-url>
cd bot/discovery-agent
python3 discover.py "https://.../ingest" "YOUR_TOKEN"
# Or edit config.yaml and run: python3 discover.py
```

### Quick Test: Check Endpoint

Test if the endpoint is accessible:
```bash
curl -I "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/agent.zip"
# Should return: Content-Type: application/zip
# If it returns: Content-Type: text/html, the endpoint is failing
```
