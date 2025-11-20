"""
Local connector for running commands on the agent server itself
"""
import asyncio
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class LocalConnector(InfrastructureConnector):
    """Local connector for running commands on the agent server itself"""
    
    async def execute_command(self, command: str, connection_config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Execute command locally"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command.split(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace'),
                "exit_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out after {timeout} seconds",
                "exit_code": -1
            }
        except Exception as e:
            logger.error(f"Local execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }


