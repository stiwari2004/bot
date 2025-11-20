"""
GCP IAP connector for executing commands through GCP IAP secure tunnel
"""
import asyncio
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class GcpIapConnector(InfrastructureConnector):
    """Connector that executes commands through GCP IAP secure tunnel (simulated)."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        project = connection_config.get("project_id")
        zone = connection_config.get("zone")
        instance = connection_config.get("instance_name")

        if not project or not zone or not instance:
            return {
                "success": False,
                "output": "",
                "error": "GCP IAP connector requires project_id, zone, and instance_name.",
                "exit_code": -1,
                "connection_error": True,
            }

        exec_command = (command or "").strip() or "uname -a"
        await asyncio.sleep(min(0.5, 0.1 + len(exec_command) * 0.01))
        output = (
            f"[gcp-iap:{project}/{zone}/{instance}] {exec_command}"
        )
        return {
            "success": True,
            "output": output,
            "error": "",
            "exit_code": 0,
            "connection_error": False,
        }




