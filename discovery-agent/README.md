# Resolvify Discovery Scanner

**One command** discovers this host, network devices (routers, switches), and storage (SAN/NAS), and sends everything to Resolvify. Works on **Windows**, **Linux**, and **macOS**. No config file. No separate install.

---

## One step

1. In Resolvify go to **Tenant Admin → Discovery**.
2. Click **Generate token** and copy the token (shown once).
3. Copy the **one command** shown on that page (Linux/macOS or Windows), replace `YOUR_TOKEN` with the token you copied, and run it in a terminal on the machine you want to scan.

That command fetches the scanner, installs dependencies, and runs full discovery (this host + network + storage). Nothing to install or configure by hand.

**Requirements:** Python 3.6+ and network access to your Resolvify app. The command uses your app’s ingest URL; you only paste your token.

---

## What gets discovered

- **This host** (Windows, Linux, or macOS)
- **Network devices** (routers, switches) if you add a `config.yaml` with `network.devices` and run from the discovery-agent folder
- **Storage / SAN / NAS** if you add `storage.targets` in config
- **Remote servers** (Linux/Windows servers, databases) via SSH/WinRM from a jump server if you add `remote_servers.servers` in config

By default the one command reports this host. For network, storage, and remote servers, copy the discovery-agent folder, add a `config.yaml` with devices/targets/servers, and run **`./discover`** from that folder (or `./discover "https://.../ingest" YOUR_TOKEN` with no config). On Debian/Ubuntu use `./discover` so dependencies install into a venv and you avoid the "externally-managed-environment" error—do not run `sudo pip3 install`.

---

## Optional: config for network, storage, and remote servers

If you have the discovery-agent folder (e.g. from the repo), you can add a `config.yaml` (from `config.sample.yaml`) and configure:

- **Network devices**: Set `network.enabled: true` with a list of `devices` (routers, switches)
- **Storage**: Set `storage.enabled: true` with `targets` (SAN/NAS)
- **Remote servers**: Set `remote_servers.enabled: true` with `servers` list (Linux/Windows servers, databases accessible via SSH/WinRM from a jump server)

Then run **`./discover`** from that folder (Linux/macOS) so the same run includes all configured scanners. On Windows use `python run.py config.yaml`.

### Remote servers from jump server

To discover multiple servers from a jump server:

1. **If running discovery ON the jump server**: Set `remote_servers.enabled: true` and list your servers in `remote_servers.servers`. Omit `jump_server` section.

2. **If running discovery FROM another machine**: Configure `remote_servers.jump_server` with jump server credentials, then list target servers in `remote_servers.servers`.

The scanner supports:
- **Linux/Unix servers** via SSH (auto-detects OS, collects hostname, IPs, OS version, CPU, memory, disk)
- **Windows servers** via WinRM (collects hostname, IPs, Windows version, CPU, memory, disk)
- **Database servers** (PostgreSQL, MySQL, MSSQL, MongoDB) - detects if port is open
- **Auto-detection**: If `os_type` is not specified, tries SSH first, then WinRM

Example `config.yaml` snippet:
```yaml
remote_servers:
  enabled: true
  timeout: 30
  jump_server:
    host: "jump.example.com"
    username: "admin"
    password: "secret"
  servers:
    - host: "192.168.1.10"
      os_type: "linux"
      username: "ubuntu"
      password: "secret"
    - host: "192.168.1.20"
      os_type: "windows"
      username: "Administrator"
      password: "secret"
      port: 5985
```

---

## Security

- Keep the token secret; do not commit or log it.
- Use HTTPS for your Resolvify URL in production.
