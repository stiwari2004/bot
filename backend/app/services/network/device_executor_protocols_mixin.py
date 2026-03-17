"""
Mixin: Telnet, API, vendor formatting, backup/rollback for NetworkDeviceExecutor
"""
import asyncio
from typing import Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class NetworkDeviceProtocolsMixin:
    """Telnet/API/config operations for NetworkDeviceExecutor."""

    async def _execute_telnet(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str,
    ) -> Dict[str, Any]:
        """Execute command via Telnet"""
        import telnetlib

        management_ip = device.get("management_ip")
        port = device.get("management_port", 23)
        username = credential.get("username") if credential else None
        password = credential.get("password") if credential else None

        if not management_ip:
            return {"success": False, "error": "Management IP not provided", "output": "", "exit_code": 1, "protocol": "telnet", "device_ip": management_ip}

        if not username or not password:
            return {"success": False, "error": "Telnet requires username and password", "output": "", "exit_code": 1, "protocol": "telnet", "device_ip": management_ip}

        logger.info(f"Executing Telnet command on {management_ip}:{port}")

        try:
            def _run_telnet_command():
                tn = None
                try:
                    tn = telnetlib.Telnet(management_ip, port, timeout=timeout)
                    tn.read_until([b"login:", b"Login:", b"Username:", b"username:", b"User Name:"], timeout=timeout)
                    tn.write(username.encode("ascii") + b"\n")
                    tn.read_until([b"Password:", b"password:", b"Passwd:"], timeout=timeout)
                    tn.write(password.encode("ascii") + b"\n")
                    command_prompts = [b"#", b"$", b">", b"%"]
                    tn.read_until(command_prompts, timeout=timeout)
                    tn.write(command.encode("ascii") + b"\n")
                    output = tn.read_until(command_prompts, timeout=timeout).decode("ascii", errors="ignore")
                    lines = output.split("\n")
                    output = "\n".join(lines[1:-1]) if len(lines) > 2 else output.strip()
                    return {"success": True, "error": None, "output": output, "exit_code": 0, "protocol": "telnet", "device_ip": management_ip}
                except telnetlib.socket.timeout:
                    return {"success": False, "error": f"Telnet connection timeout after {timeout}s", "output": "", "exit_code": 1, "protocol": "telnet", "device_ip": management_ip}
                except Exception as e:
                    return {"success": False, "error": f"Telnet execution error: {str(e)}", "output": "", "exit_code": 1, "protocol": "telnet", "device_ip": management_ip}
                finally:
                    if tn:
                        try:
                            tn.close()
                        except Exception:
                            pass

            return await asyncio.to_thread(_run_telnet_command)
        except Exception as e:
            logger.error(f"Telnet execution failed for {management_ip}:{port}: {e}", exc_info=True)
            return {"success": False, "error": f"Telnet execution failed: {str(e)}", "output": "", "exit_code": 1, "protocol": "telnet", "device_ip": management_ip}

    async def _execute_api(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str,
    ) -> Dict[str, Any]:
        """Execute command via REST API (for devices with API support)"""
        management_ip = device.get("management_ip")
        logger.info(f"Executing API command on {management_ip} (vendor={vendor})")
        return {"success": False, "error": "API execution not yet implemented", "output": "", "exit_code": 1}

    def _format_command_for_vendor(self, command: str, vendor: str, device: Dict[str, Any]) -> str:
        """Format command based on vendor/OS type"""
        vendor_lower = vendor.lower()
        model = (device.get("model") or "").lower()

        if "cisco" in vendor_lower or "ios" in model or "nx" in model:
            if command.startswith("show") or command.startswith("display"):
                return command
            elif command.startswith("configure") or command.startswith("config"):
                return f"enable\n{command}"
            return command

        elif "juniper" in vendor_lower or "junos" in model:
            if command.startswith("show"):
                return command
            elif command.startswith("set") or command.startswith("delete"):
                return f"configure\n{command}\ncommit"
            return command

        return command

    async def backup_config(
        self,
        device: Dict[str, Any],
        credential: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Backup device configuration before making changes"""
        try:
            vendor = (device.get("vendor") or "").lower()
            model = (device.get("model") or "").lower()

            if "cisco" in vendor or "ios" in model or "nx" in model:
                backup_command = "show running-config"
            elif "juniper" in vendor or "junos" in model:
                backup_command = "show configuration"
            else:
                backup_command = "show running-config"

            result = await self.execute_command(device, backup_command, credential)
            if result["success"]:
                config = result["output"]
                logger.info(f"Backed up config for device {device.get('name')} ({len(config)} chars)")
                return config
            else:
                logger.warning(f"Failed to backup config: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"Error backing up device config: {e}", exc_info=True)
            return None

    async def rollback_config(
        self,
        device: Dict[str, Any],
        backup_config: str,
        credential: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Rollback device to previous configuration"""
        try:
            vendor = (device.get("vendor") or "").lower()
            model = (device.get("model") or "").lower()

            if "cisco" in vendor or "ios" in model or "nx" in model:
                rollback_command = "configure replace flash:backup-config"
            elif "juniper" in vendor or "junos" in model:
                rollback_command = "rollback 0"
            else:
                rollback_command = "rollback"

            result = await self.execute_command(device, rollback_command, credential)
            if result["success"]:
                logger.info(f"Rolled back config for device {device.get('name')}")
            else:
                logger.error(f"Rollback failed: {result.get('error')}")
            return result
        except Exception as e:
            logger.error(f"Error rolling back device config: {e}", exc_info=True)
            return {"success": False, "error": str(e), "output": ""}
