"""
Network device connector for executing device-level commands on network devices
Supports routers, switches, firewalls via SSH/Telnet/API
"""
import asyncio
from typing import Any, Dict, Optional
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector
from app.services.network.device_executor import NetworkDeviceExecutor

logger = get_logger(__name__)


class NetworkDeviceConnector(InfrastructureConnector):
    """Connector that executes commands directly on network devices (routers, switches, firewalls)"""

    def __init__(self):
        self.executor = NetworkDeviceExecutor()

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute command on network device
        
        connection_config should contain:
        - device: Network device info (management_ip, connection_protocol, vendor, model, etc.)
        - credential: Optional credential info (username, password, api_key)
        - device_id: Optional device ID for rollback tracking
        """
        device = connection_config.get("device") or {}
        credential = connection_config.get("credential") or {}
        
        # Extract device info
        device_info = {
            'management_ip': (
                device.get("management_ip") 
                or device.get("mgmt_ip")
                or device.get("host")
                or connection_config.get("host")
            ),
            'management_port': device.get("management_port") or connection_config.get("port", 22),
            'connection_protocol': device.get("connection_protocol") or connection_config.get("protocol", "ssh"),
            'vendor': device.get("vendor"),
            'model': device.get("model"),
            'name': device.get("name"),
        }
        
        if not device_info['management_ip']:
            return {
                "success": False,
                "output": "",
                "error": "Network device management IP is required",
                "exit_code": -1,
                "connection_error": True,
            }
        
        # Extract credential info
        credential_info = None
        if credential:
            credential_info = {
                'username': credential.get("username"),
                'password': credential.get("password") or credential.get("encrypted_password"),
                'api_key': credential.get("api_key") or credential.get("encrypted_api_key"),
            }
        
        command_text = (command or "").strip()
        if not command_text:
            command_text = "show version"  # Default command
        
        logger.info(
            f"Executing network device command: {command_text[:50]}... "
            f"on {device_info['management_ip']} via {device_info['connection_protocol']}"
        )
        
        # Execute using network device executor
        result = await self.executor.execute_command(
            device=device_info,
            command=command_text,
            credential=credential_info,
            timeout=timeout
        )
        
        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error"),
            "exit_code": result.get("exit_code", 0 if result.get("success") else 1),
            "connection_error": not result.get("success", False),
        }




