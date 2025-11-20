"""
Base class for infrastructure connectors
"""
from typing import Any, Dict


class InfrastructureConnector:
    """Base class for infrastructure connectors"""
    
    async def execute_command(self, command: str, connection_config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a command on infrastructure
        
        Returns:
        {
            "success": bool,
            "output": str,
            "error": str,
            "exit_code": int
        }
        """
        raise NotImplementedError




