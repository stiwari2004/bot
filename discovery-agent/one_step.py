#!/usr/bin/env python3
"""
One-step discovery: run with your ingest URL and token. Installs deps, runs full scan
(agent + network + storage). No config file to edit.

  python3 one_step.py "https://your-app.com/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
  python one_step.py "https://..." "TOKEN"   # Windows

When run from inside the discovery-agent folder: writes config.yaml and runs run.py.
When run from elsewhere (e.g. after curl): downloads agent.zip from the same app, extracts
it with Python's zipfile (no shell unzip needed), then runs discover.py for venv + deps, or run.py.
"""
import os
import sys
import tempfile
import zipfile
import urllib.request
import urllib.error

def _ingest_url_base(ingest_url):
    if "/api/" in ingest_url:
        return ingest_url.split("/api/")[0].rstrip("/")
    return ingest_url.rstrip("/").rsplit("/", 1)[0]

def _write_config(folder, ingest_url, token):
    path = os.path.join(folder, "config.yaml")
    content = """ingest:
  url: %r
  token: %r
  run_id: null
agent:
  enabled: true
network:
  enabled: false
  devices: []
storage:
  enabled: false
  targets: []
# Remote servers: discover Linux/Windows servers via SSH/WinRM from jump server
# To enable, set enabled: true and configure servers list below
remote_servers:
  enabled: false
  timeout: 30
  # If running FROM jump server, omit jump_server section
  # If running FROM another machine, configure jump_server:
  # jump_server:
  #   host: "jump.example.com"
  #   username: "admin"
  #   password: "secret"
  servers: []
  # Example servers (uncomment and configure):
  # - host: "192.168.1.10"
  #   os_type: "linux"
  #   username: "ubuntu"
  #   password: "secret"
  # - host: "192.168.1.20"
  #   os_type: "windows"
  #   username: "Administrator"
  #   password: "secret"
  #   port: 5985
""" % (ingest_url, token)
    with open(path, "w") as f:
        f.write(content)

def _run_from_here(ingest_url, token):
    """We're in discovery-agent folder: use discover.py (venv + deps) or run run.py."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(os.path.join(script_dir, "run_discovery.py")):
        return False
    import subprocess
    # Prefer discover.py so venv is used (avoids externally-managed-environment on Debian/Ubuntu)
    discover_py = os.path.join(script_dir, "discover.py")
    if os.path.isfile(discover_py):
        code = subprocess.run([sys.executable, discover_py, ingest_url, token], cwd=script_dir).returncode
        return None if code != 0 else True
    _write_config(script_dir, ingest_url, token)
    if os.path.isfile(os.path.join(script_dir, "requirements.txt")):
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=script_dir,
            check=False,
        )
    code = subprocess.run([sys.executable, "run.py"], cwd=script_dir).returncode
    return None if code != 0 else True  # True = success

def _download_and_run(ingest_url, token):
    """Download agent.zip from app, extract, write config, run"""
    base = _ingest_url_base(ingest_url)
    package_url = base + "/api/v1/tenant-admin/discovery/agent.zip"
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            urllib.request.urlretrieve(package_url, f.name)
            zip_path = f.name
    except Exception as e:
        print("Download failed (%s), reporting this host only." % e, file=sys.stderr)
        return _report_this_host_only(ingest_url, token)
    try:
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp)
        os.unlink(zip_path)
        # Find discovery-agent folder (top-level or inside repo folder)
        agent_dir = None
        for name in os.listdir(tmp):
            p = os.path.join(tmp, name)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "run_discovery.py")):
                agent_dir = p
                break
        if not agent_dir:
            sub = os.path.join(tmp, "discovery-agent")
            if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, "run_discovery.py")):
                agent_dir = sub
        if not agent_dir:
            print("Package layout unexpected, reporting this host only.", file=sys.stderr)
            return _report_this_host_only(ingest_url, token)
        _write_config(agent_dir, ingest_url, token)
        import subprocess
        # Prefer discover.py so a venv is created (avoids externally-managed-environment on Debian/Ubuntu)
        discover_py = os.path.join(agent_dir, "discover.py")
        if os.path.isfile(discover_py):
            code = subprocess.run(
                [sys.executable, discover_py, ingest_url, token],
                cwd=agent_dir,
            ).returncode
        else:
            reqs = os.path.join(agent_dir, "requirements.txt")
            if os.path.isfile(reqs):
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                    cwd=agent_dir,
                    check=False,
                )
            code = subprocess.run([sys.executable, "run.py"], cwd=agent_dir).returncode
        return 0 if code == 0 else 1
    except Exception as e:
        print("Setup failed: %s" % e, file=sys.stderr)
        return _report_this_host_only(ingest_url, token)

def _report_this_host_only(ingest_url, token):
    """Inline: report this host only (no network/storage)."""
    import platform
    import socket
    import json
    def hostname():
        try:
            return socket.gethostname() or "unknown"
        except Exception:
            return "unknown"
    def primary_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            pass
        try:
            return socket.gethostbyname(socket.gethostname()) or "127.0.0.1"
        except Exception:
            return "127.0.0.1"
    hostname = hostname()
    primary_ip = primary_ip()
    asset = {
        "source": "discovery_agent",
        "source_native_id": "%s:%s" % (hostname, primary_ip),
        "fingerprint": hostname,
        "name": hostname,
        "primary_ip": primary_ip,
        "ips": [primary_ip],
        "tags": {"os": "%s %s" % (platform.system(), platform.release()), "python": platform.python_version()},
    }
    payload = json.dumps({"asset": asset}).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "X-Discovery-Token": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("Reported this host.")
            return 0
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, e.read().decode("utf-8")[:500]), file=sys.stderr)
        return 1
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1

def main():
    # Prefer command-line args; fall back to env (e.g. if shell strips args)
    if len(sys.argv) >= 3:
        ingest_url = sys.argv[1].strip()
        token = sys.argv[2].strip()
    else:
        ingest_url = os.environ.get("DISCOVERY_INGEST_URL", "").strip()
        token = os.environ.get("DISCOVERY_TOKEN", "").strip()
        if len(sys.argv) > 1:
            print("Received %d argument(s); expected 2 (INGEST_URL TOKEN). Check quoting." % (len(sys.argv) - 1), file=sys.stderr)
    if not ingest_url or not token:
        if not (ingest_url or token):
            print("Usage: python3 one_step.py INGEST_URL TOKEN", file=sys.stderr)
            print("   or: set DISCOVERY_INGEST_URL and DISCOVERY_TOKEN and run: python3 one_step.py", file=sys.stderr)
            print("Example: python3 run.py \"https://app.example.com/api/v1/tenant-admin/discovery/ingest\" \"your-token\"", file=sys.stderr)
            print("(Quote the URL and token so the shell does not split them.)", file=sys.stderr)
        else:
            print("INGEST_URL and TOKEN required (from args or DISCOVERY_INGEST_URL / DISCOVERY_TOKEN).", file=sys.stderr)
        return 1
    # 1) If we're inside discovery-agent, use it
    result = _run_from_here(ingest_url, token)
    if result is True:
        return 0
    if result is False:
        # 2) Try download from app
        return _download_and_run(ingest_url, token)
    return result if isinstance(result, int) else 1

if __name__ == "__main__":
    sys.exit(main())
