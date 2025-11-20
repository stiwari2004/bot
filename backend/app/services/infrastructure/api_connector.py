"""
API connector for REST API calls
"""
import json
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class APIConnector(InfrastructureConnector):
    """API connector for REST API calls"""
    
    async def execute_command(self, command: str, connection_config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute API call
        
        command should be JSON with: {"method": "GET", "endpoint": "/api/status", "body": {...}}
        connection_config:
        {
            "base_url": "https://api.example.com",
            "api_key": "key",
            "headers": {...}
        }
        """
        try:
            import aiohttp
            
            # Parse command as JSON
            cmd_data = json.loads(command) if isinstance(command, str) else command
            method = cmd_data.get("method", "GET")
            endpoint = cmd_data.get("endpoint", "/")
            body = cmd_data.get("body")
            
            base_url = connection_config.get("base_url")
            api_key = connection_config.get("api_key")
            headers = connection_config.get("headers", {})
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response_text = await response.text()
                    
                    return {
                        "success": 200 <= response.status < 300,
                        "output": response_text,
                        "error": "" if response.status < 400 else f"HTTP {response.status}",
                        "exit_code": response.status
                    }
                    
        except Exception as e:
            logger.error(f"API execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }




