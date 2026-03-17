"""
Network Device Execution Engine
Handles SSH/Telnet/API connections to network devices (Cisco, Juniper, etc.)
Supports config backup and rollback
"""
import subprocess
import platform
from typing import Dict, Any, Optional

from app.core.logging import get_logger
from app.services.network.device_executor_ssh_mixin import NetworkDeviceSSHMixin
from app.services.network.device_executor_protocols_mixin import NetworkDeviceProtocolsMixin

logger = get_logger(__name__)


class NetworkDeviceExecutor(NetworkDeviceSSHMixin, NetworkDeviceProtocolsMixin):
    """Execute commands on network devices via SSH/Telnet/API"""

    def __init__(self):
        self.name = "network_device_executor"

    async def execute_command(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute a command on a network device"""
        try:
            protocol = device.get("connection_protocol", "ssh").lower()
            vendor = (device.get("vendor") or "").lower()

            if protocol == "ssh":
                return await self._execute_ssh(device, command, credential, timeout, vendor)
            elif protocol == "telnet":
                return await self._execute_telnet(device, command, credential, timeout, vendor)
            elif protocol == "api":
                return await self._execute_api(device, command, credential, timeout, vendor)
            else:
                return {"success": False, "error": f"Unsupported protocol: {protocol}", "output": "", "exit_code": 1}
        except Exception as e:
            logger.error(f"Error executing command on network device: {e}", exc_info=True)
            return {"success": False, "error": str(e), "output": "", "exit_code": 1}

    async def test_connection(
        self,
        device: Dict[str, Any],
        credential: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Test connectivity to network device"""
        try:
            management_ip = device.get("management_ip")
            protocol = device.get("connection_protocol", "ssh").lower()

            if protocol == "ssh":
                param = "-n" if platform.system().lower() == "windows" else "-c"
                result = subprocess.run(["ping", param, "1", management_ip], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return {"success": True, "message": f"Device {management_ip} is reachable", "latency_ms": None, "protocol": protocol}
                else:
                    return {"success": False, "message": f"Device {management_ip} is not reachable", "latency_ms": None, "protocol": protocol}
            else:
                return {"success": False, "message": f"Connection testing for {protocol} not yet implemented", "latency_ms": None}
        except Exception as e:
            logger.error(f"Error testing device connection: {e}", exc_info=True)
            return {"success": False, "message": str(e), "latency_ms": None}
