# Remote Servers Discovery Setup Guide

## Problem
When running discovery from a jump server, it only reports the jump server itself, not the other servers accessible via SSH.

## Solution

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

**Then on jump server:**
```bash
cd ~/discovery-agent
pip3 install -r requirements.txt
```

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
pip3 install -r requirements.txt
```

### Step 2: Install Dependencies

```bash
pip3 install -r requirements.txt
# Or: python3 -m pip install paramiko pywinrm PyYAML netmiko
```

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
