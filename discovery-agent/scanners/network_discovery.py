"""
Network discovery: port-agnostic alive detection via ping sweep.
Derives subnet from jump server IP, finds all alive hosts.
"""
import ipaddress
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple


def get_jump_server_ip() -> Optional[str]:
    """Get primary IP of this host (jump server)."""
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
        return None


def derive_subnet(ip: str, prefix_len: int = 24) -> Optional[str]:
    """
    Derive subnet CIDR from IP. E.g. 192.168.48.10 + /24 -> 192.168.48.0/24
    """
    try:
        addr = ipaddress.IPv4Address(ip)
        if addr.is_loopback or addr.is_link_local:
            return None
        network = ipaddress.IPv4Network(f"{ip}/{prefix_len}", strict=False)
        return str(network)
    except Exception:
        return None


def _ping_alive(ip: str, timeout: int = 2) -> bool:
    """Check if host responds to ping. Cross-platform: uses system ping."""
    try:
        # Linux: ping -c 1 -W timeout
        # Windows: ping -n 1 -w (timeout*1000) ms
        import platform
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
                capture_output=True,
                timeout=timeout + 2,
            )
        else:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(timeout), ip],
                capture_output=True,
                timeout=timeout + 2,
            )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def ping_sweep(subnet: str, timeout: int = 2, max_workers: int = 50) -> List[str]:
    """
    Ping sweep: find all alive hosts in subnet (port-agnostic).
    Returns list of IP strings.
    """
    try:
        network = ipaddress.IPv4Network(subnet, strict=False)
    except Exception:
        return []

    hosts = []
    for addr in network.hosts():
        hosts.append(str(addr))

    alive = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_ping_alive, ip, timeout): ip for ip in hosts}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                if future.result():
                    alive.append(ip)
            except Exception:
                pass
    return sorted(alive)


def discover_alive_hosts(
    scan_subnets: Optional[List[str]] = None,
    prefix_len: int = 24,
    timeout: int = 2,
) -> List[str]:
    """
    Discover all alive hosts. Port-agnostic (ping only).
    If scan_subnets is None/empty, derives from jump server IP.
    Returns list of alive IPs (deduplicated).
    """
    subnets = list(scan_subnets or [])
    if not subnets:
        jump_ip = get_jump_server_ip()
        if jump_ip:
            derived = derive_subnet(jump_ip, prefix_len)
            if derived:
                subnets = [derived]

    if not subnets:
        return []

    seen = set()
    result = []
    for subnet in subnets:
        alive = ping_sweep(subnet, timeout=timeout)
        for ip in alive:
            if ip not in seen:
                seen.add(ip)
                result.append(ip)
    return sorted(result)
