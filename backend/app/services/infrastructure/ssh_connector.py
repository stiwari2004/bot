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

    _DEFAULT_CONNECT_TIMEOUT = 15
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
            "bastion_host": "jump.example.com",  # Optional: connect via bastion/ProxyJump
            "bastion_port": 22,
            "bastion_username": "jump_user",
            "bastion_password": "...",
            "bastion_private_key": "...",
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
        # Support key-based auth: credential may store key in api_key; connector expects private_key
        private_key = connection_config.get("private_key") or connection_config.get("api_key")
        passphrase = connection_config.get("passphrase") or connection_config.get("private_key_passphrase")
        connect_timeout = int(connection_config.get("connect_timeout") or self._DEFAULT_CONNECT_TIMEOUT)
        max_retries = max(1, int(connection_config.get("retries") or self._DEFAULT_RETRIES))
        retry_delay = float(connection_config.get("retry_delay_seconds") or self._DEFAULT_RETRY_DELAY)
        command_text = (command or "").strip() or "echo 'No command provided'"
        shell = connection_config.get("shell") or "bash"
        # Use connect_timeout for TCP/SSH handshake so we fail fast; use step timeout for command only
        command_timeout = max(10, int(timeout) if timeout else 60)

        deadline = time.monotonic() + (max_retries * (connect_timeout + retry_delay) + command_timeout)
        attempts = 0
        last_result: Optional[Dict[str, Any]] = None

        while attempts < max_retries and time.monotonic() < deadline:
            attempts += 1
            attempt_start = time.monotonic()
            time_left = deadline - time.monotonic()
            if time_left <= 0:
                break
            result = await self._run_via_paramiko(
                command_text,
                host,
                port,
                username,
                password,
                private_key,
                passphrase,
                connection_config=connection_config,
                connect_timeout=connect_timeout,
                command_timeout=min(command_timeout, max(10, int(time_left))),
                shell=shell,
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
        connection_config: Optional[Dict[str, Any]] = None,
        connect_timeout: int = 15,
        command_timeout: float = 60,
        shell: str = "bash",
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

        cfg = connection_config or {}
        bastion_host = (cfg.get("bastion_host") or "").strip()
        use_bastion = bool(bastion_host)

        def _execute() -> Dict[str, Any]:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = None
            if private_key:
                pkey = _load_private_key()
            try:
                bastion_client = None
                if use_bastion:
                    channel, bastion_client = self._connect_via_bastion(
                        bastion_host=bastion_host,
                        bastion_port=int(cfg.get("bastion_port") or 22),
                        bastion_username=(cfg.get("bastion_username") or "").strip() or username,
                        bastion_password=cfg.get("bastion_password"),
                        bastion_private_key=cfg.get("bastion_private_key") or cfg.get("bastion_api_key"),
                        bastion_passphrase=cfg.get("bastion_passphrase") or cfg.get("bastion_private_key_passphrase"),
                        target_host=host,
                        target_port=port,
                        connect_timeout=connect_timeout,
                        _load_key=_load_private_key,
                    )
                    logger.info(
                        "SSH connect %s:%s via bastion %s (connect_timeout=%ss)",
                        host, port, bastion_host, connect_timeout,
                    )
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        pkey=pkey,
                        sock=channel,
                        timeout=connect_timeout,
                        banner_timeout=connect_timeout,
                        auth_timeout=connect_timeout,
                        look_for_keys=False,
                        allow_agent=False,
                    )
                else:
                    logger.info(
                        "SSH connect %s:%s (connect_timeout=%ss)",
                        host, port, connect_timeout,
                    )
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        pkey=pkey,
                        timeout=connect_timeout,
                        banner_timeout=connect_timeout,
                        auth_timeout=connect_timeout,
                        look_for_keys=False,
                        allow_agent=False,
                    )
                logger.info(
                    "SSH connected to %s:%s, executing command (command_timeout=%ss)",
                    host, port, command_timeout,
                )
                # Resolve sudo password: dedicated field takes priority, then SSH login password
                sudo_password = (cfg.get("sudo_password") or "").strip() or (password or "").strip()
                # Detect if any sudo call in the command needs password injection
                import re as _re
                needs_sudo_stdin = (
                    bool(_re.search(r'\bsudo\b', command))
                    and bool(sudo_password)
                )
                exec_command = command
                if needs_sudo_stdin:
                    # Add -S (stdin password) and -p '' (no prompt text) to every sudo that
                    # doesn't already carry -S, so paramiko stdin can supply the password.
                    exec_command = _re.sub(
                        r'\bsudo\b(?!\s+-S)(?!\s+-p\s+\S+\s+-S)',
                        "sudo -S -p ''",
                        command,
                    )
                shell_lower = (shell or "").lower()
                if not shell_lower:
                    full_command = exec_command
                elif shell_lower.startswith("power"):
                    full_command = f"powershell -Command {shlex.quote(exec_command)}"
                elif shell_lower in {"bash", "sh", "zsh", "ksh"}:
                    full_command = f"{shell_lower} -lc {shlex.quote(exec_command)}"
                else:
                    full_command = f"{shell} -c {shlex.quote(exec_command)}"
                stdin, stdout, stderr = client.exec_command(full_command, timeout=int(command_timeout))
                if needs_sudo_stdin:
                    # Write password once; covers sequential sudo calls in the same command
                    try:
                        stdin.write(sudo_password + "\n")
                        stdin.flush()
                        stdin.channel.shutdown_write()
                    except Exception:
                        pass
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
                err_msg = str(exc)
                if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                    err_msg = f"SSH connection timed out to {host}:{port} (connect_timeout={connect_timeout}s). Check network, firewall, and that the host is reachable."
                return {
                    "success": False,
                    "output": "",
                    "error": err_msg,
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
                if bastion_client is not None:
                    with contextlib.suppress(Exception):
                        bastion_client.close()

        return await asyncio.to_thread(_execute)

    def _connect_via_bastion(
        self,
        bastion_host: str,
        bastion_port: int,
        bastion_username: str,
        bastion_password: Optional[str],
        bastion_private_key: Optional[str],
        bastion_passphrase: Optional[str],
        target_host: str,
        target_port: int,
        connect_timeout: int,
        _load_key,
    ):
        """
        Connect to bastion and open a direct-tcpip channel to target.
        Returns (channel, bastion_client). Caller must close bastion_client when done.
        """
        import paramiko

        bastion_client = paramiko.SSHClient()
        bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        bastion_pkey = None
        if bastion_private_key:
            key_stream = io.StringIO((bastion_private_key or "").strip())
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
                    bastion_pkey = key_cls.from_private_key(key_stream, password=bastion_passphrase)
                    break
                except Exception:
                    continue
        bastion_client.connect(
            hostname=bastion_host,
            port=bastion_port,
            username=bastion_username,
            password=bastion_password,
            pkey=bastion_pkey,
            timeout=connect_timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        transport = bastion_client.get_transport()
        if not transport:
            bastion_client.close()
            raise ValueError("Bastion connection has no transport")
        channel = transport.open_channel(
            "direct-tcpip", (target_host, target_port), ("", 0)
        )
        return (channel, bastion_client)
