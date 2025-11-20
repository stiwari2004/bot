"""
WinRM connector for Windows servers
"""
import asyncio
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class WinRMConnector(InfrastructureConnector):
    """WinRM connector for Windows servers (simulated for POC)."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        host = connection_config.get("host")
        if not host:
            return {
                "success": False,
                "output": "",
                "error": "WinRM connector missing host.",
                "exit_code": -1,
                "connection_error": True,
            }

        username = connection_config.get("username") or "administrator"
        domain = connection_config.get("domain")
        shell = (connection_config.get("shell") or "powershell").lower()
        command_text = (command or "").strip() or "Write-Host 'No command provided'"

        try:
            from pypsrp.client import Client  # type: ignore

            full_username = f"{domain}\\{username}" if domain else username
            use_ssl = bool(connection_config.get("use_ssl", False))
            port = int(connection_config.get("port") or (5986 if use_ssl else 5985))
            auth = connection_config.get("auth", "negotiate")

            client = Client(
                host,
                username=full_username,
                password=connection_config.get("password"),
                ssl=use_ssl,
                port=port,
                auth=auth,
                cert_validation=connection_config.get("cert_validation", False),
            )

            def run_command() -> Dict[str, Any]:
                if shell.startswith("power"):
                    output, streams, had_errors = client.execute_ps(command_text)
                    stderr = ""
                    if hasattr(streams, "error"):
                        stderr = "".join(str(stream) for stream in streams.error)  # type: ignore[attr-defined]
                    stdout = output
                    if not stdout and hasattr(streams, "output"):
                        stdout = "".join(str(stream) for stream in streams.output)  # type: ignore[attr-defined]
                    return {
                        "success": not had_errors,
                        "output": stdout,
                        "error": stderr,
                        "exit_code": 0 if not had_errors else 1,
                    }
                rc, stdout, stderr = client.execute_cmd(command_text)
                return {
                    "success": rc == 0,
                    "output": stdout,
                    "error": stderr,
                    "exit_code": rc,
                }

            result = await asyncio.wait_for(asyncio.to_thread(run_command), timeout=timeout)
            result["connection_error"] = False
            return result
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"WinRM command timed out after {timeout} seconds",
                "exit_code": -1,
                "connection_error": True,
            }
        except ImportError:
            # Fallback simulation when pypsrp is not installed.
            await asyncio.sleep(min(1.0, max(0.1, len(command_text) * 0.02)))
            full_username = f"{domain}\\{username}" if domain else username
            return {
                "success": True,
                "output": f"[simulated winrm:{host}] ({full_username}) {command_text}",
                "error": "",
                "exit_code": 0,
                "connection_error": False,
            }
        except Exception as exc:
            logger.error("WinRM execution error: %s", exc)
            return {
                "success": False,
                "output": "",
                "error": str(exc),
                "exit_code": -1,
                "connection_error": True,
            }




