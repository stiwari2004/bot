"""
Main orchestrator for remote server scanning.
Coordinates discoverers based on server configuration.
"""
from typing import Any, Dict, List, Optional

from .discoverers import DatabaseDiscoverer, LinuxDiscoverer, WindowsDiscoverer


def scan_remote_servers(
    servers: List[Dict[str, Any]],
    jump_config: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Scan remote servers (Linux/Windows) via SSH/WinRM from jump server.
    
    Each server config can have:
      - host (required)
      - os_type: "linux" or "windows" (default: "linux")
      - username, password (required for SSH, required for WinRM)
      - port: SSH port (default 22) or WinRM port (default 5985)
      - use_keys / key_file (optional, for SSH key auth)
      - use_https (optional, for WinRM, default False)
      - db_type (optional): if set, treat as database server (postgresql, mysql, mssql, mongodb)
      - database (optional): database name for DB discovery
    
    jump_config (optional):
      - host: jump server hostname/IP
      - port: SSH port (default 22)
      - username, password (or use_keys/key_file)
    
    Returns list of asset dicts (one per discovered server).
    """
    import sys
    assets = []
    
    for server in servers:
        host = server.get("host") or server.get("ip")
        if not host:
            continue
        
        try:
            asset = _discover_server(server, jump_config, timeout)
            if asset:
                assets.append(asset)
                print(f"  ✓ Discovered {host}", file=sys.stderr)
            else:
                username = server.get("username", "unknown")
                auth_method = "SSH keys" if server.get("use_keys") else "password"
                print(f"  ✗ Failed to connect to {host} (user: {username}, auth: {auth_method})", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ Error scanning {host}: {e}", file=sys.stderr)
    
    return assets


def _discover_server(
    server: Dict[str, Any],
    jump_config: Optional[Dict[str, Any]],
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """Discover a single server based on its configuration."""
    host = server.get("host") or server.get("ip")
    os_type = (server.get("os_type") or "linux").lower()
    username = server.get("username", "")
    password = server.get("password")
    port = int(server.get("port", 22 if os_type == "linux" else 5985))
    use_keys = bool(server.get("use_keys"))
    key_file = server.get("key_file")
    db_type = server.get("db_type")
    
    # Database discovery
    if db_type:
        return DatabaseDiscoverer.discover(
            host=host,
            db_type=db_type,
            username=username,
            password=password or "",
            port=server.get("db_port") or port,
            database=server.get("database"),
            jump_config=jump_config,
            timeout=timeout,
        )
    
    # Linux/Unix via SSH
    if os_type in ("linux", "unix", "ubuntu", "centos", "rhel", "debian"):
        return LinuxDiscoverer.discover(
            host=host,
            username=username,
            password=password,
            port=port,
            key_file=key_file,
            use_keys=use_keys,
            jump_config=jump_config,
            timeout=timeout,
        )
    
    # Windows via WinRM
    if os_type in ("windows", "win", "winrm"):
        return WindowsDiscoverer.discover(
            host=host,
            username=username,
            password=password or "",
            port=port,
            use_https=bool(server.get("use_https", False)),
            jump_config=jump_config,
            timeout=timeout,
        )
    
    # Auto-detect: try SSH first, then WinRM
    asset = LinuxDiscoverer.discover(
        host=host,
        username=username,
        password=password,
        port=port,
        key_file=key_file,
        use_keys=use_keys,
        jump_config=jump_config,
        timeout=timeout,
    )
    
    if not asset and password:
        asset = WindowsDiscoverer.discover(
            host=host,
            username=username,
            password=password,
            port=5985,
            use_https=False,
            jump_config=jump_config,
            timeout=timeout,
        )
    
    return asset
