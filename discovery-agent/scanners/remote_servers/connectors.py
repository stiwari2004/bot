"""
Connection handlers for SSH and WinRM.
Handles direct connections and jump server proxying.
"""
from typing import Any, Dict, Optional

try:
    import paramiko
    from paramiko import SSHClient, AutoAddPolicy
    from paramiko.ssh_exception import SSHException, AuthenticationException, BadHostKeyException
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import winrm
    WINRM_AVAILABLE = True
except ImportError:
    WINRM_AVAILABLE = False


class SSHConnector:
    """Handles SSH connections, including jump server proxying."""
    
    @staticmethod
    def create_client() -> Optional[SSHClient]:
        """Create and configure SSH client."""
        if not PARAMIKO_AVAILABLE:
            return None
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        return client
    
    @staticmethod
    def connect_direct(
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        use_keys: bool = False,
        timeout: int = 30,
    ) -> Optional[SSHClient]:
        """Connect directly to a host via SSH."""
        client = SSHConnector.create_client()
        if not client:
            return None
        
        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password if not use_keys else None,
                key_filename=key_file if use_keys else None,
                timeout=timeout,
                look_for_keys=use_keys and not key_file,
            )
            return client
        except (SSHException, AuthenticationException, BadHostKeyException, OSError):
            try:
                client.close()
            except Exception:
                pass
            return None
    
    @staticmethod
    def connect_via_jump(
        jump_config: Dict[str, Any],
        target_host: str,
        target_port: int,
        target_username: str,
        target_password: Optional[str] = None,
        target_key_file: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[SSHClient]:
        """
        Connect to target host via jump server using SSH tunnel.
        Returns SSHClient connected to target, or None on failure.
        """
        if not PARAMIKO_AVAILABLE:
            return None
        
        jump_host = jump_config.get("host")
        jump_port = jump_config.get("port", 22)
        jump_username = jump_config.get("username", "root")
        jump_password = jump_config.get("password")
        jump_key_file = jump_config.get("key_file")
        jump_use_keys = jump_config.get("use_keys", False)
        
        if not jump_host:
            return None
        
        jump_client = None
        try:
            # Connect to jump server
            jump_client = SSHConnector.connect_direct(
                host=jump_host,
                port=jump_port,
                username=jump_username,
                password=jump_password,
                key_file=jump_key_file,
                use_keys=jump_use_keys,
                timeout=timeout,
            )
            
            if not jump_client:
                return None
            
            # Create transport channel through jump server
            jump_transport = jump_client.get_transport()
            if not jump_transport:
                jump_client.close()
                return None
            
            # Open channel to target through jump server
            dest_addr = (target_host, target_port)
            local_addr = (jump_host, jump_port)
            channel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)
            
            # Create new SSH client for target
            target_client = SSHConnector.create_client()
            if not target_client:
                channel.close()
                jump_client.close()
                return None
            
            # Connect to target via channel
            target_client.connect(
                hostname=target_host,
                port=target_port,
                username=target_username,
                password=target_password,
                key_filename=target_key_file,
                sock=channel,
                timeout=timeout,
                look_for_keys=bool(target_key_file),
            )
            
            return target_client
            
        except (SSHException, AuthenticationException, BadHostKeyException, OSError, Exception):
            if jump_client:
                try:
                    jump_client.close()
                except Exception:
                    pass
            return None


class WinRMConnector:
    """Handles WinRM connections for Windows servers."""
    
    @staticmethod
    def create_session(
        host: str,
        port: int,
        username: str,
        password: str,
        use_https: bool = False,
    ) -> Optional[Any]:
        """
        Create WinRM session. Returns session object or None on failure.
        Note: WinRM through jump server requires SSH port forwarding (not implemented yet).
        """
        if not WINRM_AVAILABLE:
            return None
        
        try:
            protocol = "https" if use_https else "http"
            endpoint = f"{protocol}://{host}:{port}/wsman"
            
            session = winrm.Session(
                endpoint,
                auth=(username, password),
                transport="ntlm" if use_https else "plaintext",
                server_cert_validation="ignore" if not use_https else "validate",
            )
            return session
        except Exception:
            return None
