"""
Network scanner: discover routers, switches, firewalls via SSH (Netmiko) and/or SNMP.
Runs from a central host; does not run on the devices.
"""
import re
import subprocess
from typing import Any, Dict, List, Optional

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

SOURCE = "network_scanner"


def _snmp_get(host: str, community: str, oid: str, timeout: int = 5) -> Optional[str]:
    """Run snmpget; returns value or None. Requires net-snmp (snmpget) on PATH."""
    try:
        out = subprocess.run(
            ["snmpget", "-v2c", "-c", community, "-t", str(timeout), "-Oqv", host, oid],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def discover_via_snmp(host: str, community: str = "public", port: int = 161) -> Optional[Dict[str, Any]]:
    """
    Discover one device via SNMP (sysName, sysDescr). Uses snmpget (net-snmp).
    Returns asset dict or None if SNMP fails.
    """
    # OIDs: 1.3.6.1.2.1.1.1.0 = sysDescr, 1.3.6.1.2.1.1.5.0 = sysName
    target = host if port == 161 else f"{host}:{port}"
    name = _snmp_get(target, community, "1.3.6.1.2.1.1.5.0")
    descr = _snmp_get(target, community, "1.3.6.1.2.1.1.1.0")
    if not name and not descr:
        return None
    name = (name or "unknown").strip()
    source_native_id = f"{host}:{name}"
    tags = {"source": "snmp"}
    if descr:
        tags["description"] = descr[:500]
    return {
        "source": SOURCE,
        "source_native_id": source_native_id,
        "fingerprint": name,
        "name": name,
        "primary_ip": host,
        "ips": [host],
        "tags": tags,
    }


def discover_via_ssh(
    host: str,
    device_type: str,
    username: str,
    password: str,
    port: int = 22,
    use_keys: bool = False,
    key_file: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Discover one device via SSH (Netmiko). Returns asset dict or None on failure.
    device_type: e.g. cisco_ios, juniper_junos, arista_eos.
    """
    if not NETMIKO_AVAILABLE:
        return None
    conn_params = {
        "device_type": device_type,
        "host": host,
        "username": username,
        "password": password,
        "port": port,
    }
    if use_keys or key_file:
        conn_params["use_keys"] = True
        if key_file:
            conn_params["key_file"] = key_file
    try:
        with ConnectHandler(**conn_params) as conn:
            prompt = conn.find_prompt()
            hostname = prompt.rstrip(">#").strip() or host
            # Try to get version / model info
            try:
                ver = conn.send_command("show version", read_timeout=30)
            except Exception:
                ver = ""
            model = _parse_model(device_type, ver)
            tags = {"source": "ssh", "device_type": device_type}
            if model:
                tags["model"] = model
            source_native_id = f"{host}:{hostname}"
            return {
                "source": SOURCE,
                "source_native_id": source_native_id,
                "fingerprint": hostname,
                "name": hostname,
                "primary_ip": host,
                "ips": [host],
                "tags": tags,
            }
    except (NetmikoTimeoutException, NetmikoAuthenticationException, OSError, Exception):
        return None


def _parse_model(device_type: str, ver_text: str) -> str:
    """Extract model/vendor line from show version output."""
    if not ver_text:
        return ""
    ver_text = ver_text[:2000]
    if "cisco" in device_type.lower():
        m = re.search(r"(?:cisco\s+)?(\S+\s+\d+.*?)(?:\s+with|\s+processor|$)", ver_text, re.I | re.S)
        if m:
            return m.group(1).strip().split("\n")[0][:200]
        m = re.search(r"Model Number\s*:\s*(\S+)", ver_text, re.I)
        if m:
            return m.group(1).strip()
    if "juniper" in device_type.lower():
        m = re.search(r"Model:\s*(\S+)", ver_text, re.I)
        if m:
            return m.group(1).strip()
    if "arista" in device_type.lower():
        m = re.search(r"Arista\s+(\S+)", ver_text, re.I)
        if m:
            return m.group(1).strip()
    return ""


def scan_network_devices(
    devices: List[Dict[str, Any]],
    snmp_community: Optional[str] = None,
    prefer_ssh: bool = True,
) -> List[Dict[str, Any]]:
    """
    Scan a list of network devices. Each device config can have:
      - host (required)
      - device_type (for SSH, e.g. cisco_ios, juniper_junos, arista_eos)
      - username, password (for SSH)
      - port (optional, default 22)
      - use_keys / key_file (optional, for SSH key auth)
      - snmp_only (optional): if true, only use SNMP (skip SSH)
    If snmp_community is set, SNMP is tried when SSH is not configured or fails.
    Returns list of asset dicts (one per discovered device).
    """
    assets = []
    for dev in devices:
        host = dev.get("host") or dev.get("ip")
        if not host:
            continue
        asset = None
        if prefer_ssh and not dev.get("snmp_only"):
            device_type = dev.get("device_type", "cisco_ios")
            username = dev.get("username", "")
            password = dev.get("password", "")
            if username or dev.get("key_file"):
                asset = discover_via_ssh(
                    host=str(host),
                    device_type=device_type,
                    username=username or "admin",
                    password=password or "",
                    port=int(dev.get("port", 22)),
                    use_keys=bool(dev.get("use_keys")),
                    key_file=dev.get("key_file"),
                )
        if asset is None and (snmp_community or dev.get("snmp_community")):
            community = dev.get("snmp_community") or snmp_community or "public"
            asset = discover_via_snmp(host=str(host), community=community, port=int(dev.get("snmp_port", 161)))
        if asset:
            assets.append(asset)
    return assets
