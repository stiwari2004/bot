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
    
    current_user = getpass.getuser()
    
    # Don't try to SSH to ourselves (we already report this host via run_agent_self)
    try:
        _self_hostname = socket.gethostname() or ""
        _self_short = _self_hostname.split(".")[0] if _self_hostname else ""
    except Exception:
        _self_hostname = _self_short = ""
    try:
        _self_ip = None
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        _self_ip = s.getsockname()[0]
        s.close()
    except Exception:
        _self_ip = None
    
    def _is_self(host):
        if not host:
            return True
        # Skip hashed known_hosts entries (e.g. |1|base64|base64|) - we can't connect to those
        if host.startswith("|1|") or (host.startswith("|") and "|" in host[1:]):
            return True
        if host in ("localhost", "127.0.0.1", "::1"):
            return True
        if _self_ip and host == _self_ip:
            return True
        if _self_hostname and host == _self_hostname:
            return True
        if _self_short and host == _self_short:
            return True
        if _self_short and host.startswith(_self_short + "."):
            return True
        return False
    
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
                    hostname = parts[-1]
                    if ip in ("127.0.0.1", "::1", "localhost") or hostname in ("localhost", "localhost.localdomain"):
                        continue
                    if _is_self(ip) or _is_self(hostname):
                        continue
                    if not (ip.startswith(("192.168.", "10.", "172.")) or ":" not in ip):
                        continue
                    host = hostname if not all(c.isdigit() or c == '.' for c in hostname.split('.')[0]) else ip
                    if _is_self(host) or any(s.get("host") == host for s in servers):
                        continue
                    servers.append({
                        "host": host,
                        "os_type": "linux",
                        "username": current_user,
                        "use_keys": True,
                    })
    except Exception:
        pass
    
    # Read ~/.ssh/known_hosts (skip hashed entries: |1|...)
    ssh_dir = os.path.expanduser("~/.ssh")
    known_hosts = os.path.join(ssh_dir, "known_hosts")
    try:
        if os.path.isfile(known_hosts):
            with open(known_hosts, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if not parts:
                        continue
                    host_part = parts[0]
                    for host in host_part.split(","):
                        host = host.strip()
                        if _is_self(host):
                            continue
                        if host.startswith("[") and host.endswith("]"):
                            continue  # [hostname]:port format - could parse but skip for simplicity
                        if any(s.get("host") == host for s in servers):
                            continue
                        servers.append({
                            "host": host,
                            "os_type": "linux",
                            "username": current_user,
                            "use_keys": True,
                        })
    except Exception:
        pass
    
    return servers


def _run_network_discovery(nd_cfg: dict, config: dict, run_agent_self_fn) -> list:
    """
    Phase 1: Ping sweep (port-agnostic). Phase 2: Fingerprint. Phase 3: Full scan.
    Returns list of assets.
    """
    import getpass
    from scanners.network_discovery import discover_alive_hosts, get_jump_server_ip
    from scanners.fingerprint import fingerprint_alive_hosts

    scan_subnets = nd_cfg.get("scan_subnets") or []
    prefix_len = int(nd_cfg.get("prefix_len", 24))
    timeout = int(nd_cfg.get("ping_timeout", 2))
    remote_cfg = config.get("remote_servers") or {}
    username = remote_cfg.get("default_username") or getpass.getuser()
    use_keys = remote_cfg.get("use_keys", True)
    winrm_password = remote_cfg.get("default_winrm_password") or nd_cfg.get("winrm_password")
    snmp_community = (config.get("network") or {}).get("snmp_community") or nd_cfg.get("snmp_community") or "public"

    print("Phase 1: Ping sweep (port-agnostic)...", file=sys.stderr)
    alive = discover_alive_hosts(scan_subnets=scan_subnets, prefix_len=prefix_len, timeout=timeout)
    self_ip = get_jump_server_ip()
    if self_ip and self_ip in alive:
        alive = [ip for ip in alive if ip != self_ip]
    print(f"  Found {len(alive)} alive hosts", file=sys.stderr)
    if not alive:
        return []

    print("Phase 2: Fingerprinting (hostname, OS)...", file=sys.stderr)
    targets = fingerprint_alive_hosts(
        alive,
        self_ip=self_ip,
        username=username,
        use_keys=use_keys,
        key_file=remote_cfg.get("key_file"),
        winrm_password=winrm_password,
        snmp_community=snmp_community,
    )

    all_assets = []
    remote_targets = []
    snmp_targets = []
    unknown_targets = []

    for t in targets:
        ot = (t.get("os_type") or "unknown").lower()
        if ot in ("linux", "unix", "ubuntu", "centos", "rhel", "debian", "windows", "win", "winrm"):
            remote_targets.append(t)
        elif ot in ("postgresql", "mysql", "mssql", "mongodb") or t.get("db_type"):
            remote_targets.append(t)
        elif ot == "snmp":
            snmp_targets.append({"host": t["host"], "snmp_only": True, "snmp_community": snmp_community})
        elif ot == "unknown":
            if t.get("open_ports") and 22 in t.get("open_ports", {}):
                # Port 22 open, try SSH
                t["os_type"] = "linux"
                remote_targets.append(t)
            else:
                # No open ports or no SSH - report as alive
                unknown_targets.append(t)
        elif ot == "synology":
            unknown_targets.append(t)
        else:
            unknown_targets.append(t)

    # Full scan: remote servers (Linux, Windows, DBs)
    if remote_targets:
        try:
            from scanners.remote_servers import scan_remote_servers
            print(f"Phase 3: Full inventory of {len(remote_targets)} hosts...", file=sys.stderr)
            remote_assets = scan_remote_servers(
                servers=remote_targets,
                jump_config=remote_cfg.get("jump_server"),
                timeout=int(remote_cfg.get("timeout", 30)),
            )
            all_assets.extend(remote_assets)
            print(f"  Discovered {len(remote_assets)}/{len(remote_targets)} servers", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: remote scan failed: {e}", file=sys.stderr)

    # SNMP devices
    if snmp_targets:
        try:
            from scanners.network import scan_network_devices
            net_assets = scan_network_devices(snmp_targets, snmp_community=snmp_community, prefer_ssh=False)
            all_assets.extend(net_assets)
            print(f"  Discovered {len(net_assets)} SNMP devices", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: SNMP scan failed: {e}", file=sys.stderr)

    # Minimal assets for hosts we couldn't full-scan (synology, unknown)
    for t in unknown_targets:
        tags = {"discovered": "alive"}
        if t.get("os_type") == "synology":
            tags["type"] = "synology_dsm"
            tags["port"] = "5001"
        elif t.get("open_ports"):
            tags["open_ports"] = str(list(t["open_ports"].keys()))
        else:
            tags["note"] = "no common ports open"
        all_assets.append({
            "source": "network_discovery",
            "source_native_id": f"{t['host']}:{t.get('os_type', 'alive')}",
            "fingerprint": t.get("hostname", t["host"]),
            "name": t.get("hostname", t["host"]) or t["host"],
            "primary_ip": t["host"],
            "ips": [t["host"]],
            "tags": tags,
        })

    return all_assets


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

    # Network discovery: ping sweep (port-agnostic) -> fingerprint -> full scan
    nd_cfg = config.get("network_discovery") or {}
    auto_scan = os.environ.get("DISCOVERY_AUTO_SCAN", "").lower() in ("1", "true", "yes")
    ran_network_discovery = False
    if nd_cfg.get("enabled") or auto_scan:
        if not nd_cfg.get("enabled"):
            nd_cfg = {**nd_cfg, "enabled": True}
        _assets = _run_network_discovery(nd_cfg, config, run_agent_self)
        all_assets.extend(_assets)
        ran_network_discovery = True

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
    servers_to_scan = list(remote_cfg.get("servers") or [])
    
    # Auto-discover from /etc/hosts and ~/.ssh/known_hosts when on Linux (skip if network_discovery already ran)
    if not ran_network_discovery and (auto_scan or not servers_to_scan):
        import platform
        if platform.system() == "Linux":
            discovered = _auto_discover_local_servers()
            if discovered:
                servers_to_scan = discovered
                print(f"Auto-discovered {len(discovered)} servers from /etc/hosts and ~/.ssh/known_hosts", file=sys.stderr)
                print("Note: Using SSH key auth. If connections fail, add passwords in config.yaml", file=sys.stderr)
                sys.stderr.flush()
    
    # Scan whenever we have servers to scan (from config or auto-discovery)
    if servers_to_scan:
        try:
            from scanners.remote_servers import scan_remote_servers
            print(f"Scanning {len(servers_to_scan)} remote servers...", file=sys.stderr)
            sys.stderr.flush()
            jump_config = remote_cfg.get("jump_server")
            timeout = int(remote_cfg.get("timeout", 30))
            remote_assets = scan_remote_servers(
                servers=servers_to_scan,
                jump_config=jump_config,
                timeout=timeout,
            )
            print(f"Successfully discovered {len(remote_assets)}/{len(servers_to_scan)} servers", file=sys.stderr)
            all_assets.extend(remote_assets)
        except ImportError as e:
            print(f"Warning: remote_servers scanner not available: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        except Exception as e:
            print(f"Warning: remote servers scan failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

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
