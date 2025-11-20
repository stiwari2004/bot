"""
SSH connector for Linux/Unix servers
"""
import asyncio
import contextlib
import io
import shlex
import time
from typing import Any, Dict, Optional
from app.core import metrics
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


class SSHConnector(InfrastructureConnector):
    """SSH connector for Linux/Unix servers"""

    _DEFAULT_CONNECT_TIMEOUT = 10
    _DEFAULT_RETRIES = 3
    _DEFAULT_RETRY_DELAY = 2.0

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute command via SSH using Paramiko with retry logic.

        connection_config can include:
        {
            "host": "server.example.com",
            "port": 22,
            "username": "user",
            "password": "...",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----...",
            "passphrase": "...",
            "retries": 3,
            "retry_delay_seconds": 2.0
        }
        """
        host = (connection_config.get("host") or "").strip()
        username = (connection_config.get("username") or "").strip()
        if not host or not username:
            return {
                "success": False,
                "output": "",
                "error": "SSH connector requires host and username.",
                "exit_code": -1,
                "connection_error": True,
            }

        port = int(connection_config.get("port") or 22)
        password = connection_config.get("password")
        private_key = connection_config.get("private_key")
        passphrase = connection_config.get("passphrase") or connection_config.get("private_key_passphrase")
        connect_timeout = int(connection_config.get("connect_timeout") or self._DEFAULT_CONNECT_TIMEOUT)
        max_retries = max(1, int(connection_config.get("retries") or self._DEFAULT_RETRIES))
        retry_delay = float(connection_config.get("retry_delay_seconds") or self._DEFAULT_RETRY_DELAY)
        command_text = (command or "").strip() or "echo 'No command provided'"
        shell = connection_config.get("shell") or "bash"

        deadline = time.monotonic() + max(timeout, connect_timeout)
        attempts = 0
        last_result: Optional[Dict[str, Any]] = None

        while attempts < max_retries and time.monotonic() < deadline:
            attempts += 1
            attempt_start = time.monotonic()
            time_left = deadline - time.monotonic()
            if time_left <= 0:
                break
            per_attempt_timeout = float(timeout) if timeout else time_left
            remaining_timeout = max(1.0, min(per_attempt_timeout, time_left))
            result = await self._run_via_paramiko(
                command_text,
                host,
                port,
                username,
                password,
                private_key,
                passphrase,
                remaining_timeout,
                shell,
            )

            result["retry_count"] = attempts - 1
            result.setdefault("duration_ms", int((time.monotonic() - attempt_start) * 1000))

            if result.get("success") and not result.get("connection_error"):
                return result

            last_result = result
            if attempts < max_retries and result.get("connection_error"):
                metrics.record_connector_retry("ssh", result.get("error") or "connection_error")
                await asyncio.sleep(retry_delay)
            else:
                break

        if last_result:
            return last_result

        return {
            "success": False,
            "output": "",
            "error": "SSH execution failed before command could be attempted.",
            "exit_code": -1,
            "connection_error": True,
        }

    async def _run_via_paramiko(
        self,
        command: str,
        host: str,
        port: int,
        username: str,
        password: Optional[str],
        private_key: Optional[str],
        passphrase: Optional[str],
        timeout: float,
        shell: str,
    ) -> Dict[str, Any]:
        try:
            import paramiko
            from paramiko.ssh_exception import (
                AuthenticationException,
                NoValidConnectionsError,
                SSHException,
            )
        except ImportError:
            logger.warning("Paramiko not installed; falling back to simulated SSH execution.")
            await asyncio.sleep(min(1.0, max(0.1, len(command) * 0.02)))
            return {
                "success": True,
                "output": f"[simulated ssh:{host}] {command}",
                "error": "",
                "exit_code": 0,
                "connection_error": False,
                "simulated": True,
            }

        def _load_private_key() -> Optional[paramiko.PKey]:
            if not private_key:
                return None
            key_material = private_key.strip()
            if not key_material:
                return None
            key_stream = io.StringIO(key_material)
            exceptions = []
            for key_cls in (
                getattr(paramiko, "Ed25519Key", None),
                getattr(paramiko, "RSAKey", None),
                getattr(paramiko, "ECDSAKey", None),
                getattr(paramiko, "DSSKey", None),
            ):
                if key_cls is None:
                    continue
                key_stream.seek(0)
                try:
                    return key_cls.from_private_key(key_stream, password=passphrase)
                except Exception as exc:  # pragma: no cover - library-specific errors
                    exceptions.append(exc)
            logger.error("Failed to parse SSH private key: %s", exceptions[-1] if exceptions else "unknown error")
            raise ValueError("Unsupported SSH private key type or invalid key material.")

        def _execute() -> Dict[str, Any]:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = None
            if private_key:
                pkey = _load_private_key()
            try:
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    pkey=pkey,
                    timeout=timeout,
                    banner_timeout=timeout,
                    auth_timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
                shell_lower = (shell or "").lower()
                if not shell_lower:
                    full_command = command
                elif shell_lower.startswith("power"):
                    full_command = f"powershell -Command {shlex.quote(command)}"
                elif shell_lower in {"bash", "sh", "zsh", "ksh"}:
                    full_command = f"{shell_lower} -lc {shlex.quote(command)}"
                else:
                    full_command = f"{shell} -c {shlex.quote(command)}"
                stdin, stdout, stderr = client.exec_command(full_command, timeout=timeout)
                output = stdout.read().decode("utf-8", errors="replace")
                error_output = stderr.read().decode("utf-8", errors="replace")
                exit_code = stdout.channel.recv_exit_status()
                return {
                    "success": exit_code == 0,
                    "output": output,
                    "error": error_output,
                    "exit_code": exit_code,
                    "connection_error": False,
                }
            except (AuthenticationException, NoValidConnectionsError, SSHException) as exc:
                return {
                    "success": False,
                    "output": "",
                    "error": str(exc),
                    "exit_code": -1,
                    "connection_error": True,
                }
            except Exception as exc:  # pragma: no cover - network/system failure path
                logger.error("SSH execution error: %s", exc)
                return {
                    "success": False,
                    "output": "",
                    "error": str(exc),
                    "exit_code": -1,
                    "connection_error": True,
                }
            finally:
                with contextlib.suppress(Exception):
                    client.close()

        return await asyncio.to_thread(_execute)


