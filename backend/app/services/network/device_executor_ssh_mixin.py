"""
Mixin: SSH execution methods for NetworkDeviceExecutor
"""
import asyncio
from typing import Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class NetworkDeviceSSHMixin:
    """SSH execution operations for NetworkDeviceExecutor."""

    async def _execute_ssh(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str,
    ) -> Dict[str, Any]:
        """Execute command via SSH using asyncssh (preferred) or paramiko (fallback)"""
        management_ip = device.get("management_ip")
        if not management_ip:
            return {"success": False, "error": "Management IP address is required", "output": "", "exit_code": 1}

        port = device.get("management_port", 22)
        username = credential.get("username") if credential else None
        password = credential.get("password") if credential else None

        if not username or not password:
            return {"success": False, "error": "SSH credentials (username/password) required", "output": "", "exit_code": 1}

        formatted_command = self._format_command_for_vendor(command, vendor, device)
        logger.info(f"Executing SSH command on {management_ip}:{port} (vendor={vendor}, command={formatted_command[:50]}...)")

        try:
            import asyncssh
            return await self._execute_ssh_asyncssh(management_ip, port, username, password, formatted_command, timeout, vendor)
        except ImportError:
            logger.debug("asyncssh not available, trying paramiko")
            try:
                return await self._execute_ssh_paramiko(management_ip, port, username, password, formatted_command, timeout, vendor)
            except ImportError:
                return {
                    "success": False,
                    "error": "Neither asyncssh nor paramiko is installed. Install one: pip install asyncssh or pip install paramiko",
                    "output": "",
                    "exit_code": 1,
                }
        except Exception as e:
            logger.error(f"SSH execution failed with asyncssh: {e}", exc_info=True)
            try:
                return await self._execute_ssh_paramiko(management_ip, port, username, password, formatted_command, timeout, vendor)
            except Exception as e2:
                logger.error(f"SSH execution failed with paramiko: {e2}", exc_info=True)
                return {"success": False, "error": f"SSH execution failed: {str(e)}", "output": "", "exit_code": 1}

    async def _execute_ssh_asyncssh(
        self, host: str, port: int, username: str, password: str, command: str, timeout: int, vendor: str
    ) -> Dict[str, Any]:
        """Execute SSH command using asyncssh library"""
        import asyncssh

        try:
            async with asyncssh.connect(
                host, port=port, username=username, password=password,
                known_hosts=None, connect_timeout=timeout, login_timeout=timeout,
            ) as conn:
                result = await conn.run(command, timeout=timeout)
                return {
                    "success": result.exit_status == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.exit_status != 0 else None,
                    "exit_code": result.exit_status,
                    "protocol": "ssh",
                    "device_ip": host,
                }
        except asyncssh.Error as e:
            logger.error(f"asyncssh connection error: {e}")
            return {"success": False, "error": f"SSH connection failed: {str(e)}", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}
        except asyncio.TimeoutError:
            return {"success": False, "error": f"SSH command timed out after {timeout} seconds", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}

    async def _execute_ssh_paramiko(
        self, host: str, port: int, username: str, password: str, command: str, timeout: int, vendor: str
    ) -> Dict[str, Any]:
        """Execute SSH command using paramiko library (fallback)"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._run_paramiko_command, host, port, username, password, command, timeout)
        except Exception as e:
            logger.error(f"paramiko execution error: {e}")
            return {"success": False, "error": f"SSH execution failed: {str(e)}", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}

    def _run_paramiko_command(
        self, host: str, port: int, username: str, password: str, command: str, timeout: int
    ) -> Dict[str, Any]:
        """Synchronous paramiko command execution (runs in executor)"""
        import paramiko
        from paramiko.ssh_exception import SSHException, AuthenticationException

        client = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout, look_for_keys=False, allow_agent=False)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="replace")
            error_output = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            return {
                "success": exit_code == 0,
                "output": output,
                "error": error_output if exit_code != 0 else None,
                "exit_code": exit_code,
                "protocol": "ssh",
                "device_ip": host,
            }
        except AuthenticationException as e:
            return {"success": False, "error": f"SSH authentication failed: {str(e)}", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}
        except SSHException as e:
            return {"success": False, "error": f"SSH connection error: {str(e)}", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}
        except Exception as e:
            return {"success": False, "error": f"SSH execution failed: {str(e)}", "output": "", "exit_code": 1, "protocol": "ssh", "device_ip": host}
        finally:
            if client:
                client.close()
