"""
Server fingerprinting utility for license activation
Generates unique server identifier based on hardware/system characteristics
"""
import hashlib
import platform
import socket
import os
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServerFingerprint:
    """Generate unique server fingerprint for license activation"""
    
    @staticmethod
    def get_fingerprint() -> str:
        """
        Generate unique server fingerprint based on:
        - Machine ID (/etc/machine-id or Windows machine GUID)
        - Hostname
        - MAC address
        - Docker container ID (if applicable)
        
        Returns:
            SHA256 hash of server characteristics (64 char hex string)
        """
        components = []
        
        # 1. Machine ID (most reliable on Linux)
        machine_id = ServerFingerprint._get_machine_id()
        if machine_id:
            components.append(f"machine_id:{machine_id}")
        
        # 2. Hostname
        hostname = socket.gethostname()
        components.append(f"hostname:{hostname}")
        
        # 3. MAC address (first non-loopback interface)
        mac_address = ServerFingerprint._get_mac_address()
        if mac_address:
            components.append(f"mac:{mac_address}")
        
        # 4. Docker container ID (if running in Docker)
        container_id = ServerFingerprint._get_container_id()
        if container_id:
            components.append(f"container:{container_id}")
        
        # 5. System platform info
        system_info = f"{platform.system()}:{platform.machine()}:{platform.processor()}"
        components.append(f"platform:{system_info}")
        
        # Combine and hash
        combined = "|".join(components)
        fingerprint = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        logger.debug(f"Generated server fingerprint: {fingerprint[:16]}... (from {len(components)} components)")
        return fingerprint
    
    @staticmethod
    def _get_machine_id() -> Optional[str]:
        """Get machine ID from /etc/machine-id (Linux) or Windows registry"""
        try:
            # Linux
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
            
            # macOS
            if os.path.exists("/etc/hostid"):
                with open("/etc/hostid", "r") as f:
                    return f.read().strip()
            
            # Windows - try to get machine GUID from registry
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\Cryptography"
                    )
                    machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                    winreg.CloseKey(key)
                    return machine_guid
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Could not read machine ID: {e}")
        
        return None
    
    @staticmethod
    def _get_mac_address() -> Optional[str]:
        """Get MAC address of first non-loopback network interface"""
        try:
            import uuid
            mac = uuid.getnode()
            if mac:
                # Convert to hex string
                mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                                   for elements in range(0, 8*6, 8)][::-1])
                # Skip if all zeros or loopback
                if mac_str != "00:00:00:00:00:00":
                    return mac_str
        except Exception as e:
            logger.debug(f"Could not get MAC address: {e}")
        
        return None
    
    @staticmethod
    def _get_container_id() -> Optional[str]:
        """Get Docker container ID if running in container"""
        try:
            # Check cgroup (Linux containers)
            if os.path.exists("/proc/self/cgroup"):
                with open("/proc/self/cgroup", "r") as f:
                    for line in f:
                        if "docker" in line or "containerd" in line:
                            # Extract container ID
                            parts = line.strip().split("/")
                            for part in parts:
                                if len(part) == 64:  # Docker container ID is 64 chars
                                    return part[:12]  # Return short ID
        except Exception as e:
            logger.debug(f"Could not get container ID: {e}")
        
        return None
    
    @staticmethod
    def get_hostname() -> str:
        """Get server hostname"""
        return socket.gethostname()
    
    @staticmethod
    def get_system_info() -> dict:
        """Get system information for telemetry"""
        return {
            "hostname": ServerFingerprint.get_hostname(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "is_docker": ServerFingerprint._get_container_id() is not None,
        }

