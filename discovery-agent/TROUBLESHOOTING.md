# Discovery Agent Troubleshooting

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

**Then on jump server:**
```bash
cd ~/discovery-agent
pip3 install -r requirements.txt
# Edit config.yaml to enable remote_servers
python3 run.py config.yaml
```

### Alternative: Git Clone (if repo is accessible)

If the repo is on GitHub/GitLab:
```bash
git clone <repo-url>
cd bot/discovery-agent
pip3 install -r requirements.txt
# Edit config.yaml
python3 run.py config.yaml
```

### Quick Test: Check Endpoint

Test if the endpoint is accessible:
```bash
curl -I "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/agent.zip"
# Should return: Content-Type: application/zip
# If it returns: Content-Type: text/html, the endpoint is failing
```
