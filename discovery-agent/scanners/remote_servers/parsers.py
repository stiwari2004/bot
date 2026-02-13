"""
Data parsers for extracting information from command outputs.
Parses Linux shell output and Windows PowerShell output.
"""
import json
from typing import Any, Dict, List, Optional


class LinuxParser:
    """Parse Linux/Unix command outputs into structured data."""
    
    @staticmethod
    def parse_hostname(output: str) -> str:
        """Extract hostname from hostname command output."""
        return output.strip() or ""
    
    @staticmethod
    def parse_ips(output: str, fallback_output: str = "") -> List[str]:
        """
        Parse IP addresses from hostname -I or ip addr output.
        Returns list of non-loopback IPv4 addresses.
        """
        ips = []
        
        # Try hostname -I first (space-separated)
        if output:
            ips = [ip.strip() for ip in output.split() if ip.strip() and not ip.startswith("127.")]
        
        # Fallback to ip addr show output
        if not ips and fallback_output:
            for line in fallback_output.split("\n"):
                if "inet " in line:
                    try:
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[1].split("/")[0]
                            if ip and not ip.startswith("127."):
                                ips.append(ip)
                    except Exception:
                        pass
        
        return ips[:10]  # Limit to 10 IPs
    
    @staticmethod
    def parse_os_info(uname_output: str, os_release_output: str) -> str:
        """Extract OS information from uname and /etc/os-release."""
        # Default to uname output
        os_info = uname_output[:200].strip() if uname_output else "Linux"
        
        # Try to get prettier name from os-release
        if os_release_output:
            for line in os_release_output.split("\n"):
                if line.startswith("PRETTY_NAME="):
                    os_info = line.split("=", 1)[1].strip('"').strip("'")
                    break
                elif line.startswith("NAME=") and "PRETTY_NAME" not in os_release_output:
                    os_info = line.split("=", 1)[1].strip('"').strip("'")
        
        return os_info
    
    @staticmethod
    def build_tags(
        os_info: str,
        hostname: str,
        cpu_cores: Optional[str] = None,
        disk_info: Optional[str] = None,
        memory_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build tags dictionary from parsed data."""
        tags = {
            "os": os_info,
            "os_type": "linux",
            "hostname": hostname,
        }
        if cpu_cores:
            tags["cpu_cores"] = cpu_cores
        if disk_info:
            tags["disk_info"] = disk_info[:500]
        if memory_info:
            tags["memory_info"] = memory_info[:200]
        return tags


class WindowsParser:
    """Parse Windows PowerShell command outputs into structured data."""
    
    @staticmethod
    def parse_hostname(output: str) -> str:
        """Extract hostname from PowerShell output."""
        return output.strip() or ""
    
    @staticmethod
    def parse_ips(output: str) -> List[str]:
        """Parse IP addresses from Get-NetIPAddress output."""
        ips = []
        for line in output.split("\n"):
            ip = line.strip()
            if ip and not ip.startswith("127.") and "." in ip:
                ips.append(ip)
        return ips[:10]
    
    @staticmethod
    def parse_computer_info(output: str) -> Dict[str, Any]:
        """Parse Get-ComputerInfo JSON output."""
        try:
            return json.loads(output) if output else {}
        except json.JSONDecodeError:
            return {}
    
    @staticmethod
    def parse_disk_info(output: str) -> Dict[str, Any]:
        """Parse Get-WmiObject Win32_LogicalDisk JSON output."""
        try:
            disks = json.loads(output) if output else []
            return {"disk_count": str(len(disks)) if isinstance(disks, list) else "0"}
        except json.JSONDecodeError:
            return {}
    
    @staticmethod
    def build_tags(
        hostname: str,
        computer_info: Dict[str, Any],
        disk_info: Dict[str, Any],
        cpu_cores: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build tags dictionary from parsed Windows data."""
        os_info = computer_info.get("WindowsProductName", "") or "Windows"
        memory = computer_info.get("TotalPhysicalMemory", 0)
        
        tags = {
            "os": os_info,
            "os_type": "windows",
            "hostname": hostname,
        }
        
        if memory:
            tags["total_memory_bytes"] = str(memory)
        
        tags.update(disk_info)
        
        if cpu_cores:
            tags["cpu_cores"] = cpu_cores
        
        return tags
