"""
Auto-discovery helper: detect servers accessible from jump server.
Scans common IP ranges or uses SSH to list known hosts.
"""
from typing import Any, Dict, List, Optional

try:
    import paramiko
    from paramiko import SSHClient
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

from .connectors import SSHConnector


def auto_discover_servers_from_jump(
    jump_config: Dict[str, Any],
    ip_ranges: Optional[List[str]] = None,
    known_hosts_file: Optional[str] = None,
    timeout: int = 5,
) -> List[Dict[str, Any]]:
    """
    Auto-discover servers accessible from jump server.
    
    Methods:
    1. Read /etc/hosts or known_hosts to get hostnames
    2. Scan common IP ranges (if provided)
    3. Try SSH connection to common ports
    
    Returns list of server config dicts (host, username inferred from jump_config).
    """
    servers = []
    
    if not PARAMIKO_AVAILABLE:
        return servers
    
    # Method 1: Read known hosts from jump server
    jump_client = None
    try:
        jump_client = SSHConnector.connect_direct(
            host=jump_config.get("host"),
            port=jump_config.get("port", 22),
            username=jump_config.get("username", "root"),
            password=jump_config.get("password"),
            key_file=jump_config.get("key_file"),
            use_keys=jump_config.get("use_keys", False),
            timeout=timeout,
        )
        
        if jump_client:
            # Try to read /etc/hosts
            try:
                stdin, stdout, stderr = jump_client.exec_command("cat /etc/hosts | grep -v '^#' | grep -v '^$' | awk '{print $NF}' | sort -u", timeout=5)
                hosts_output = stdout.read().decode("utf-8", errors="ignore").strip()
                for hostname in hosts_output.split("\n"):
                    hostname = hostname.strip()
                    if hostname and hostname not in ("localhost", "localhost.localdomain"):
                        # Try to resolve IP
                        try:
                            stdin2, stdout2, stderr2 = jump_client.exec_command(f"getent hosts {hostname} | awk '{{print $1}}' | head -1", timeout=3)
                            ip = stdout2.read().decode("utf-8", errors="ignore").strip()
                            if ip and ip.startswith(("192.168.", "10.", "172.")):
                                servers.append({
                                    "host": ip,
                                    "os_type": "linux",  # Default assumption
                                    "username": jump_config.get("username", "root"),
                                    "password": jump_config.get("password"),
                                    "use_keys": jump_config.get("use_keys", False),
                                    "key_file": jump_config.get("key_file"),
                                })
                        except Exception:
                            pass
            except Exception:
                pass
            
            # Try to read SSH known_hosts
            try:
                stdin, stdout, stderr = jump_client.exec_command("cat ~/.ssh/known_hosts 2>/dev/null | awk '{print $1}' | cut -d, -f1 | sort -u", timeout=5)
                known_hosts = stdout.read().decode("utf-8", errors="ignore").strip()
                for host in known_hosts.split("\n"):
                    host = host.strip()
                    if host and not host.startswith("#") and host not in ("localhost", "127.0.0.1"):
                        # Skip if already added
                        if not any(s.get("host") == host for s in servers):
                            servers.append({
                                "host": host,
                                "os_type": "linux",
                                "username": jump_config.get("username", "root"),
                                "password": jump_config.get("password"),
                                "use_keys": jump_config.get("use_keys", False),
                                "key_file": jump_config.get("key_file"),
                            })
            except Exception:
                pass
                
    except Exception:
        pass
    finally:
        if jump_client:
            try:
                jump_client.close()
            except Exception:
                pass
    
    return servers
