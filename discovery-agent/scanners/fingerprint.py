"""
Fingerprint discovered hosts: probe ports, classify type, get hostname/OS.
Takes alive IPs from network_discovery, returns targets for full inventory scan.
"""
import socket
import sys
from typing import Any, Dict, List, Optional

# Ports to probe for classification (port -> type hint)
COMMON_PORTS = {
    22: "linux",      # SSH
    5985: "windows",  # WinRM HTTP
    5986: "windows",  # WinRM HTTPS
    5432: "postgresql",
    3306: "mysql",
    1433: "mssql",
    27017: "mongodb",
    161: "snmp",
    5001: "synology",
}

PROBE_TIMEOUT = 2


def _tcp_open(host: str, port: int, timeout: int = PROBE_TIMEOUT) -> bool:
    """Check if TCP port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def probe_ports(ip: str, ports: Optional[List[int]] = None) -> Dict[int, str]:
    """Probe which ports are open on a host. Returns {port: type} for open ports."""
    to_probe = ports or list(COMMON_PORTS.keys())
    open_ports = {}
    for port in to_probe:
        if _tcp_open(ip, port):
            open_ports[port] = COMMON_PORTS.get(port, "unknown")
    return open_ports


def _quick_ssh_fingerprint(ip: str, username: str, use_keys: bool = True, key_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Quick SSH: hostname + uname. Returns {hostname, os_info} or None."""
    try:
        from scanners.remote_servers.connectors import SSHConnector
        client = SSHConnector.connect_direct(
            host=ip,
            port=22,
            username=username,
            password=None,
            key_file=key_file,
            use_keys=use_keys,
            timeout=5,
        )
        if not client:
            return None
        try:
            stdin, stdout, stderr = client.exec_command("hostname", timeout=5)
            hostname = stdout.read().decode("utf-8", errors="ignore").strip() or ip
            stdin2, stdout2, stderr2 = client.exec_command("uname -s 2>/dev/null || echo Linux", timeout=5)
            os_raw = stdout2.read().decode("utf-8", errors="ignore").strip()
            return {"hostname": hostname, "os_info": os_raw or "Linux", "os_type": "linux"}
        finally:
            try:
                client.close()
            except Exception:
                pass
    except Exception:
        pass
    return None


def _quick_snmp_fingerprint(ip: str, community: str = "public") -> Optional[Dict[str, Any]]:
    """Quick SNMP: sysName. Returns {hostname, os_info} or None."""
    try:
        from scanners.network import discover_via_snmp
        asset = discover_via_snmp(ip, community=community)
        if asset:
            return {
                "hostname": asset.get("name", ip),
                "os_info": asset.get("tags", {}).get("description", "network_device")[:200],
                "os_type": "snmp",
            }
    except Exception:
        pass
    return None


def fingerprint_host(
    ip: str,
    open_ports: Dict[int, str],
    username: str,
    use_keys: bool = True,
    key_file: Optional[str] = None,
    winrm_password: Optional[str] = None,
    snmp_community: str = "public",
) -> Dict[str, Any]:
    """
    Fingerprint a single host: get hostname and OS where possible.
    Returns dict suitable for remote_servers or network scanner input.
    """
    result = {
        "host": ip,
        "hostname": ip,
        "os_type": "unknown",
        "open_ports": open_ports,
    }

    # Prefer SSH if port 22 open (Linux or network device)
    if 22 in open_ports:
        fp = _quick_ssh_fingerprint(ip, username, use_keys, key_file)
        if fp:
            result["hostname"] = fp.get("hostname", ip)
            result["os_info"] = fp.get("os_info", "")
            result["os_type"] = "linux"
            result["username"] = username
            result["use_keys"] = use_keys
            if key_file:
                result["key_file"] = key_file
            return result

    # SNMP if port 161 open
    if 161 in open_ports:
        fp = _quick_snmp_fingerprint(ip, snmp_community)
        if fp:
            result["hostname"] = fp.get("hostname", ip)
            result["os_info"] = fp.get("os_info", "")
            result["os_type"] = "snmp"
            result["snmp_community"] = snmp_community
            return result

    # WinRM if 5985/5986 open (we can't easily quick-fingerprint without password)
    if 5985 in open_ports or 5986 in open_ports:
        result["os_type"] = "windows"
        result["port"] = 5986 if 5986 in open_ports else 5985
        if winrm_password:
            result["username"] = username or "Administrator"
            result["password"] = winrm_password

    # DB ports: just mark type
    if 5432 in open_ports:
        result["os_type"] = "postgresql"
        result["db_type"] = "postgresql"
    elif 3306 in open_ports:
        result["os_type"] = "mysql"
        result["db_type"] = "mysql"
    elif 1433 in open_ports:
        result["os_type"] = "mssql"
        result["db_type"] = "mssql"
    elif 27017 in open_ports:
        result["os_type"] = "mongodb"
        result["db_type"] = "mongodb"

    # Synology
    if 5001 in open_ports:
        result["os_type"] = "synology"

    # Unknown but alive - try SSH with default user (might be Linux we couldn't auth to)
    if result["os_type"] == "unknown" and 22 in open_ports:
        result["os_type"] = "linux"  # Assume Linux, will try full scan
        result["username"] = username
        result["use_keys"] = use_keys

    return result


def fingerprint_alive_hosts(
    alive_ips: List[str],
    self_ip: Optional[str] = None,
    username: str = "",
    use_keys: bool = True,
    key_file: Optional[str] = None,
    winrm_password: Optional[str] = None,
    snmp_community: str = "public",
) -> List[Dict[str, Any]]:
    """
    Fingerprint all alive IPs. Skip self. Returns list of target dicts for full scan.
    """
    import getpass
    if not username:
        username = getpass.getuser()

    targets = []
    for ip in alive_ips:
        if self_ip and ip == self_ip:
            continue
        open_ports = probe_ports(ip)
        if not open_ports:
            # Alive but no common ports - still report as "unknown" for visibility
            targets.append({
                "host": ip,
                "hostname": ip,
                "os_type": "unknown",
                "open_ports": {},
                "username": username,
                "use_keys": use_keys,
            })
            continue
        fp = fingerprint_host(
            ip, open_ports, username, use_keys, key_file,
            winrm_password, snmp_community,
        )
        targets.append(fp)
    return targets
