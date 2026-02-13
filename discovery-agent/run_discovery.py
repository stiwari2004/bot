#!/usr/bin/env python3
"""
Unified discovery runner: load config (YAML), run agent + network + storage scanners,
and POST all assets to the Resolvify ingest API.
Usage:
  python run_discovery.py [config.yaml]
  If no config: uses env DISCOVERY_INGEST_URL, DISCOVERY_TOKEN and runs agent-only (like discovery_agent.py).
"""
import os
import sys

# Add parent dir so we can import ingest_client and discovery_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest_client import post_asset, post_assets_batch

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_config(path: str) -> dict:
    if not YAML_AVAILABLE:
        return {}
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _auto_discover_local_servers() -> list:
    """Auto-discover servers from local /etc/hosts and ~/.ssh/known_hosts when running on jump server."""
    servers = []
    import socket
    import os.path
    import getpass
    
    # Get current username for SSH connections
    current_user = getpass.getuser()
    
    # Read /etc/hosts
    try:
        with open("/etc/hosts", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    hostname = parts[-1]  # Last part is usually hostname
                    # Skip localhost and loopback
                    if ip not in ("127.0.0.1", "::1", "localhost") and hostname not in ("localhost", "localhost.localdomain"):
                        # Only include private IPs (assumes jump server can reach them)
                        if ip.startswith(("192.168.", "10.", "172.")) or ":" not in ip:
                            # Use hostname if it's not an IP, otherwise use IP
                            host = hostname if not all(c.isdigit() or c == '.' for c in hostname.split('.')[0]) else ip
                            if host not in [s.get("host") for s in servers]:
                                servers.append({
                                    "host": host,
                                    "os_type": "linux",  # Default assumption
                                    "username": current_user,  # Use current user
                                    "use_keys": True,  # Prefer SSH keys (common on jump servers)
                                })
    except Exception:
        pass
    
    # Read ~/.ssh/known_hosts
    ssh_dir = os.path.expanduser("~/.ssh")
    known_hosts = os.path.join(ssh_dir, "known_hosts")
    try:
        if os.path.isfile(known_hosts):
            with open(known_hosts, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # known_hosts format: hostname,ip ssh-key...
                    parts = line.split()
                    if parts:
                        host_part = parts[0]
                        # Can be "hostname,ip" or just "hostname"
                        for host in host_part.split(","):
                            host = host.strip()
                            # Skip if it's an IP we already have or localhost
                            if host and host not in ("localhost", "127.0.0.1") and not host.startswith("[") and not host.endswith("]"):
                                # Skip if already added
                                if not any(s.get("host") == host for s in servers):
                                    servers.append({
                                        "host": host,
                                        "os_type": "linux",
                                        "username": current_user,
                                        "use_keys": True,
                                    })
    except Exception:
        pass
    
    return servers


def run_agent_self() -> dict:
    """Build the single host asset (same as discovery_agent.py)."""
    import platform
    import socket

    def _hostname():
        try:
            return socket.gethostname() or "unknown"
        except Exception:
            return "unknown"

    def _primary_ip():
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

    hostname = _hostname()
    primary_ip = _primary_ip()
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    return {
        "source": "discovery_agent",
        "source_native_id": f"{hostname}:{primary_ip}",
        "fingerprint": hostname,
        "name": hostname,
        "primary_ip": primary_ip,
        "ips": [primary_ip],
        "tags": {"os": os_info, "python": platform.python_version()},
    }


def main() -> int:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path) if os.path.isfile(config_path) else {}

    ingest = config.get("ingest") or {}
    ingest_url = os.environ.get("DISCOVERY_INGEST_URL", "").strip() or ingest.get("url", "").strip()
    token = os.environ.get("DISCOVERY_TOKEN", "").strip() or ingest.get("token", "").strip()
    run_id = ingest.get("run_id")
    if run_id is None and os.environ.get("DISCOVERY_RUN_ID"):
        try:
            run_id = int(os.environ.get("DISCOVERY_RUN_ID"))
        except ValueError:
            run_id = None

    if not ingest_url or not token:
        print("Set DISCOVERY_INGEST_URL and DISCOVERY_TOKEN, or provide config.yaml with ingest.url and ingest.token.", file=sys.stderr)
        return 1

    all_assets = []

    # Agent (this host)
    if config.get("agent", {}).get("enabled", True) if config else True:
        all_assets.append(run_agent_self())

    # Network devices
    net_cfg = config.get("network") or {}
    if net_cfg.get("enabled") and net_cfg.get("devices"):
        from scanners.network import scan_network_devices
        devices = scan_network_devices(
            net_cfg["devices"],
            snmp_community=net_cfg.get("snmp_community"),
            prefer_ssh=net_cfg.get("prefer_ssh", True),
        )
        all_assets.extend(devices)

    # Storage / SAN / NAS
    storage_cfg = config.get("storage") or {}
    if storage_cfg.get("enabled") and storage_cfg.get("targets"):
        from scanners.storage import scan_storage_targets
        storage_assets = scan_storage_targets(storage_cfg["targets"])
        all_assets.extend(storage_assets)

    # Remote servers (Linux/Windows via SSH/WinRM from jump server)
    remote_cfg = config.get("remote_servers") or {}
    auto_scan = os.environ.get("DISCOVERY_AUTO_SCAN", "").lower() in ("1", "true", "yes")
    
    # Auto-enable remote_servers if DISCOVERY_AUTO_SCAN is set or if enabled but servers list is empty
    if auto_scan or (remote_cfg.get("enabled") and not remote_cfg.get("servers")):
        # Try to auto-discover servers from local /etc/hosts and ~/.ssh/known_hosts
        import platform
        if platform.system() == "Linux":
            discovered_servers = _auto_discover_local_servers()
            if discovered_servers:
                if not remote_cfg.get("enabled"):
                    remote_cfg["enabled"] = True
                if not remote_cfg.get("servers"):
                    remote_cfg["servers"] = discovered_servers
                    print(f"Auto-discovered {len(discovered_servers)} servers from /etc/hosts and ~/.ssh/known_hosts", file=sys.stderr)
    
    if remote_cfg.get("enabled") and remote_cfg.get("servers"):
        try:
            from scanners.remote_servers import scan_remote_servers
            jump_config = remote_cfg.get("jump_server")
            timeout = int(remote_cfg.get("timeout", 30))
            remote_assets = scan_remote_servers(
                servers=remote_cfg["servers"],
                jump_config=jump_config,
                timeout=timeout,
            )
            all_assets.extend(remote_assets)
        except ImportError as e:
            print(f"Warning: remote_servers scanner not available: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: remote servers scan failed: {e}", file=sys.stderr)

    if not all_assets:
        print("No assets to report.", file=sys.stderr)
        return 0

    results = post_assets_batch(ingest_url, token, all_assets, run_id=run_id)
    ok = sum(1 for r in results if r.get("result", {}).get("ok"))
    print(f"Reported {ok}/{len(results)} assets.")
    for r in results:
        if not r.get("result", {}).get("ok"):
            print(f"  FAIL {r.get('asset')}: {r.get('result')}", file=sys.stderr)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
