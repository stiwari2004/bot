"""
Network cluster connector for establishing sessions to network clusters/controllers
"""
import asyncio
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class NetworkClusterConnector(InfrastructureConnector):
    """Connector that simulates establishing a session to a network cluster/controller."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        cluster = connection_config.get("cluster") or {}
        cluster_id = cluster.get("id") or connection_config.get("cluster_id")
        management_host = cluster.get("management_host") or connection_config.get("host")
        transport = cluster.get("transport") or connection_config.get("transport") or "ssh"

        if not cluster_id or not management_host:
            return {
                "success": False,
                "output": "",
                "error": "Network cluster connector requires cluster.id and management_host.",
                "exit_code": -1,
                "connection_error": True,
            }

        await asyncio.sleep(0.2)
        message = (
            f"[network-cluster:{cluster_id}] connected via {transport} "
            f"({management_host})"
        )
        logger.info(message)

        return {
            "success": True,
            "output": message,
            "error": "",
            "exit_code": 0,
            "connection_error": False,
            "cluster_id": cluster_id,
        }




