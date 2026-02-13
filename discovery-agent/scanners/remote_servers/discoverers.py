"""
Discovery logic for different server types.
Each discoverer handles OS-specific command execution and data collection.
"""
from typing import Any, Dict, List, Optional

from .connectors import SSHConnector, WinRMConnector
from .parsers import LinuxParser, WindowsParser

SOURCE = "remote_servers_scanner"


class LinuxDiscoverer:
    """Discover Linux/Unix servers via SSH."""
    
    DISCOVERY_COMMANDS = [
        "hostname",
        "hostname -I 2>/dev/null || ip addr show | grep 'inet ' | awk '{print $2}' | cut -d/ -f1 | head -5",
        "uname -a",
        "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || cat /etc/lsb-release 2>/dev/null || echo ''",
        "df -h | head -10",
        "free -h 2>/dev/null || echo ''",
        "nproc",
    ]
    
    @staticmethod
    def discover(
        host: str,
        username: str,
        password: Optional[str] = None,
        port: int = 22,
        key_file: Optional[str] = None,
        use_keys: bool = False,
        jump_config: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Discover Linux server via SSH. Returns asset dict or None on failure.
        """
        client = None
        try:
            # Connect via jump server or direct
            if jump_config:
                client = SSHConnector.connect_via_jump(
                    jump_config=jump_config,
                    target_host=host,
                    target_port=port,
                    target_username=username,
                    target_password=password,
                    target_key_file=key_file,
                    timeout=timeout,
                )
            else:
                client = SSHConnector.connect_direct(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    key_file=key_file,
                    use_keys=use_keys,
                    timeout=timeout,
                )
            
            if not client:
                return None
            
            # Execute discovery commands
            results = LinuxDiscoverer._execute_commands(client)
            
            # Parse results
            hostname = LinuxParser.parse_hostname(results.get("hostname", "")) or host
            ips = LinuxParser.parse_ips(
                results.get("hostname -I", ""),
                results.get("ip addr show", ""),
            )
            primary_ip = ips[0] if ips else host
            
            os_info = LinuxParser.parse_os_info(
                results.get("uname -a", ""),
                results.get("cat /etc/os-release", ""),
            )
            
            tags = LinuxParser.build_tags(
                os_info=os_info,
                hostname=hostname,
                cpu_cores=results.get("nproc", "").strip(),
                disk_info=results.get("df -h", ""),
                memory_info=results.get("free -h", ""),
            )
            
            # Build asset dict
            source_native_id = f"{host}:{hostname}"
            return {
                "source": SOURCE,
                "source_native_id": source_native_id,
                "fingerprint": hostname,
                "name": hostname,
                "primary_ip": primary_ip,
                "ips": ips if ips else [primary_ip],
                "tags": tags,
            }
            
        except Exception:
            return None
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
    
    @staticmethod
    def _execute_commands(client) -> Dict[str, str]:
        """Execute discovery commands and return results dict."""
        results = {}
        for cmd in LinuxDiscoverer.DISCOVERY_COMMANDS:
            try:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
                output = stdout.read().decode("utf-8", errors="ignore").strip()
                results[cmd] = output
            except Exception:
                results[cmd] = ""
        return results


class WindowsDiscoverer:
    """Discover Windows servers via WinRM."""
    
    PS_COMMANDS = [
        "$env:COMPUTERNAME",
        "Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*'} | Select-Object -ExpandProperty IPAddress",
        "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory, CsProcessors | ConvertTo-Json",
        "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace | ConvertTo-Json",
        "(Get-WmiObject Win32_ComputerSystem).NumberOfLogicalProcessors",
    ]
    
    @staticmethod
    def discover(
        host: str,
        username: str,
        password: str,
        port: int = 5985,
        use_https: bool = False,
        jump_config: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Discover Windows server via WinRM. Returns asset dict or None on failure.
        Note: WinRM through jump server not yet implemented.
        """
        if jump_config:
            # TODO: Implement WinRM via SSH tunnel
            return None
        
        session = WinRMConnector.create_session(
            host=host,
            port=port,
            username=username,
            password=password,
            use_https=use_https,
        )
        
        if not session:
            return None
        
        try:
            # Execute PowerShell commands
            results = WindowsDiscoverer._execute_commands(session)
            
            # Parse results
            hostname = WindowsParser.parse_hostname(results.get("$env:COMPUTERNAME", "")) or host
            ips = WindowsParser.parse_ips(results.get("Get-NetIPAddress", ""))
            primary_ip = ips[0] if ips else host
            
            computer_info = WindowsParser.parse_computer_info(results.get("Get-ComputerInfo", "{}"))
            disk_info = WindowsParser.parse_disk_info(results.get("Get-WmiObject Win32_LogicalDisk", "[]"))
            cpu_cores = results.get("(Get-WmiObject Win32_ComputerSystem).NumberOfLogicalProcessors", "").strip()
            
            tags = WindowsParser.build_tags(
                hostname=hostname,
                computer_info=computer_info,
                disk_info=disk_info,
                cpu_cores=cpu_cores,
            )
            
            # Build asset dict
            source_native_id = f"{host}:{hostname}"
            return {
                "source": SOURCE,
                "source_native_id": source_native_id,
                "fingerprint": hostname,
                "name": hostname,
                "primary_ip": primary_ip,
                "ips": ips if ips else [primary_ip],
                "tags": tags,
            }
            
        except Exception:
            return None
    
    @staticmethod
    def _execute_commands(session) -> Dict[str, str]:
        """Execute PowerShell commands and return results dict."""
        results = {}
        for cmd in WindowsDiscoverer.PS_COMMANDS:
            try:
                result = session.run_ps(cmd)
                if result.status_code == 0:
                    results[cmd] = result.std_out.decode("utf-8", errors="ignore").strip()
                else:
                    results[cmd] = ""
            except Exception:
                results[cmd] = ""
        return results


class DatabaseDiscoverer:
    """Discover database servers via port detection."""
    
    DEFAULT_PORTS = {
        "postgresql": 5432,
        "postgres": 5432,
        "mysql": 3306,
        "mssql": 1433,
        "sqlserver": 1433,
        "mongodb": 27017,
    }
    
    @staticmethod
    def discover(
        host: str,
        db_type: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        database: Optional[str] = None,
        jump_config: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Discover database server via port detection.
        Returns asset dict or None on failure.
        Note: DB connection via SSH tunnel not yet implemented.
        """
        if jump_config:
            # TODO: Implement DB connection via SSH tunnel
            return None
        
        db_type_lower = db_type.lower()
        
        # Determine port
        if not port:
            port = DatabaseDiscoverer.DEFAULT_PORTS.get(db_type_lower, 5432)
        
        # Test port connectivity
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                return None
        except Exception:
            return None
        
        # Build asset dict
        source_native_id = f"{host}:{port}:{db_type}"
        tags = {
            "db_type": db_type,
            "port": str(port),
        }
        if database:
            tags["database"] = database
        
        return {
            "source": SOURCE,
            "source_native_id": source_native_id,
            "fingerprint": f"{db_type}-{host}",
            "name": f"{db_type}@{host}:{port}",
            "primary_ip": host,
            "ips": [host],
            "tags": tags,
        }
