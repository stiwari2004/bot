"""
Infrastructure connectors for executing commands
POC version - simplified implementations
"""
import asyncio
import contextlib
import io
import json
import shlex
import time
from typing import Any, Dict, Optional
from app.core import metrics
from app.core.logging import get_logger

logger = get_logger(__name__)


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


class SSMConnector(InfrastructureConnector):
    """AWS SSM connector that executes commands via boto3 with retry/polling support."""

    _DEFAULT_RETRIES = 2
    _DEFAULT_RETRY_DELAY = 2.5
    _DEFAULT_POLL_SECONDS = 2.0

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        instance_id = (connection_config.get("instance_id") or "").strip()
        region = (connection_config.get("region") or "").strip()
        if not instance_id or not region:
            return {
                "success": False,
                "output": "",
                "error": "SSM connector requires instance_id and region.",
                "exit_code": -1,
                "connection_error": True,
            }

        command_text = (command or "").strip() or "echo 'No command provided'"
        document_name = connection_config.get("document_name")
        shell = (connection_config.get("shell") or "sh").lower()
        if not document_name:
            document_name = "AWS-RunPowerShellScript" if "power" in shell else "AWS-RunShellScript"

        max_retries = max(1, int(connection_config.get("retries") or self._DEFAULT_RETRIES))
        retry_delay = float(connection_config.get("retry_delay_seconds") or self._DEFAULT_RETRY_DELAY)
        poll_interval = float(connection_config.get("poll_interval_seconds") or self._DEFAULT_POLL_SECONDS)
        comment = connection_config.get("comment") or "Agent workspace manual command"
        parameters = (connection_config.get("parameters") or {}).copy()
        commands = parameters.get("commands")
        if isinstance(commands, (list, tuple)):
            commands_list = list(commands)
        elif isinstance(commands, str):
            commands_list = [commands]
        else:
            commands_list = []
        if not commands_list:
            commands_list = [command_text]
        parameters["commands"] = commands_list
        execution_timeout = int(connection_config.get("execution_timeout") or timeout or 60)

        attempts = 0
        last_result: Optional[Dict[str, Any]] = None
        while attempts < max_retries:
            attempts += 1
            result = await self._send_and_poll(
                instance_id=instance_id,
                region=region,
                document_name=document_name,
                parameters=parameters,
                timeout=execution_timeout,
                poll_interval=poll_interval,
                comment=comment,
            )
            result["retry_count"] = attempts - 1
            if result.get("success") or not result.get("connection_error"):
                return result
            last_result = result
            if attempts < max_retries:
                metrics.record_connector_retry("aws_ssm", result.get("error") or "connection_error")
                await asyncio.sleep(retry_delay)
        return last_result or {
            "success": False,
            "output": "",
            "error": "SSM execution failed before command could be attempted.",
            "exit_code": -1,
            "connection_error": True,
        }

    async def _send_and_poll(
        self,
        *,
        instance_id: str,
        region: str,
        document_name: str,
        parameters: Dict[str, Any],
        timeout: int,
        poll_interval: float,
        comment: str,
    ) -> Dict[str, Any]:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError:
            logger.warning("boto3 not installed; falling back to simulated SSM execution.")
            await asyncio.sleep(min(1.0, max(0.1, len(parameters.get("commands", [])) * 0.015 + 0.1)))
            summary = f"[simulated ssm:{instance_id}] {'; '.join(parameters.get('commands', []))}".strip()
            return {
                "success": True,
                "output": summary,
                "error": "",
                "exit_code": 0,
                "connection_error": False,
                "simulated": True,
            }

        start_time = time.monotonic()
        client = boto3.client("ssm", region_name=region)
        try:
            send_kwargs = {
                "InstanceIds": [instance_id],
                "DocumentName": document_name,
                "Parameters": parameters,
                "Comment": comment,
                "TimeoutSeconds": timeout,
            }

            response = await asyncio.to_thread(client.send_command, **send_kwargs)
            command_id = response["Command"]["CommandId"]

            deadline = start_time + timeout
            while time.monotonic() < deadline:
                try:
                    invocation = await asyncio.to_thread(
                        client.get_command_invocation,
                        CommandId=command_id,
                        InstanceId=instance_id,
                    )
                except client.exceptions.InvocationDoesNotExist:  # type: ignore[attr-defined]
                    await asyncio.sleep(poll_interval)
                    continue
                status = invocation.get("Status")
                if status in {"Success", "Failed", "Cancelled", "TimedOut"}:
                    exit_code = invocation.get("ResponseCode", 0 if status == "Success" else 1)
                    return {
                        "success": status == "Success",
                        "output": invocation.get("StandardOutputContent") or "",
                        "error": invocation.get("StandardErrorContent") or invocation.get("StatusDetails") or "",
                        "exit_code": exit_code,
                        "connection_error": status in {"Cancelled", "TimedOut"},
                        "duration_ms": int((time.monotonic() - start_time) * 1000),
                    }
                await asyncio.sleep(poll_interval)

            return {
                "success": False,
                "output": "",
                "error": f"SSM command timed out after {timeout} seconds.",
                "exit_code": -1,
                "connection_error": True,
            }
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "ClientError")
            logger.error("SSM client error: %s", exc)
            return {
                "success": False,
                "output": "",
                "error": f"{error_code}: {exc}",
                "exit_code": -1,
                "connection_error": True,
            }
        except BotoCoreError as exc:  # pragma: no cover - network/system failure path
            logger.error("SSM boto core error: %s", exc)
            return {
                "success": False,
                "output": "",
                "error": str(exc),
                "exit_code": -1,
                "connection_error": True,
            }


class DatabaseConnector(InfrastructureConnector):
    """Database connector for PostgreSQL, MySQL, etc."""
    
    async def execute_command(self, command: str, connection_config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute SQL query
        
        connection_config:
        {
            "host": "db.example.com",
            "port": 5432,
            "database": "mydb",
            "username": "user",
            "password": "password",
            "db_type": "postgresql" | "mysql" | "mssql"
        }
        """
        try:
            db_type = connection_config.get("db_type", "postgresql")
            host = connection_config.get("host")
            port = connection_config.get("port", 5432)
            database = connection_config.get("database")
            username = connection_config.get("username")
            password = connection_config.get("password")
            
            if db_type == "postgresql":
                import asyncpg
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    timeout=timeout
                )
                try:
                    result = await conn.fetch(command)
                    return {
                        "success": True,
                        "output": json.dumps([dict(row) for row in result], default=str),
                        "error": "",
                        "exit_code": 0
                    }
                finally:
                    await conn.close()
            
            elif db_type == "mysql":
                import aiomysql
                conn = await aiomysql.connect(
                    host=host,
                    port=port,
                    db=database,
                    user=username,
                    password=password,
                    connect_timeout=timeout
                )
                try:
                    cursor = await conn.cursor()
                    await cursor.execute(command)
                    result = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    await cursor.close()
                    
                    return {
                        "success": True,
                        "output": json.dumps([dict(zip(columns, row)) for row in result], default=str),
                        "error": "",
                        "exit_code": 0
                    }
                finally:
                    conn.close()
            
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Unsupported database type: {db_type}",
                    "exit_code": -1
                }
                
        except Exception as e:
            logger.error(f"Database execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }


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


class NetworkDeviceConnector(InfrastructureConnector):
    """Connector that executes device-level commands through an existing cluster session."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        cluster = connection_config.get("cluster") or {}
        device = connection_config.get("device") or {}

        cluster_id = cluster.get("id") or connection_config.get("cluster_id")
        device_id = device.get("id") or connection_config.get("device_id")
        mgmt_ip = (
            device.get("mgmt_ip")
            or device.get("host")
            or connection_config.get("host")
        )

        if not cluster_id:
            return {
                "success": False,
                "output": "",
                "error": "Network device metadata missing cluster identifier.",
                "exit_code": -1,
                "connection_error": True,
            }
        if not device_id or not mgmt_ip:
            return {
                "success": False,
                "output": "",
                "error": "Network device metadata requires device id and mgmt_ip/host.",
                "exit_code": -1,
                "connection_error": True,
            }

        command_text = (command or "").strip() or "show running-config | include hostname"
        await asyncio.sleep(min(0.5, 0.1 + len(command_text) * 0.01))

        output = (
            f"[network-device:{device_id}] via cluster {cluster_id} "
            f"({mgmt_ip}) -> {command_text}"
        )
        return {
            "success": True,
            "output": output,
            "error": "",
            "exit_code": 0,
            "connection_error": False,
        }


class AzureBastionConnector(InfrastructureConnector):
    """Connector that executes commands through Azure Bastion (simulated)."""

    async def execute_command(
        self,
        command: str,
        connection_config: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        resource_id = (
            connection_config.get("resource_id")
            or connection_config.get("target_resource_id")
        )
        bastion_host = (
            connection_config.get("bastion_host")
            or connection_config.get("bastion_resource_id")
        )
        target_host = connection_config.get("host") or connection_config.get("target_host")

        if not resource_id or not bastion_host or not target_host:
            return {
                "success": False,
                "output": "",
                "error": "Azure Bastion connector requires resource_id, bastion_host, and target_host.",
                "exit_code": -1,
                "connection_error": True,
            }

        exec_command = (command or "").strip() or "whoami"
        await asyncio.sleep(min(0.5, 0.1 + len(exec_command) * 0.01))
        output = (
            f"[azure-bastion:{target_host}] {exec_command} (resource={resource_id})"
        )
        return {
            "success": True,
            "output": output,
            "error": "",
            "exit_code": 0,
            "connection_error": False,
        }


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


def get_connector(connector_type: str) -> InfrastructureConnector:
    """Get connector instance by type"""
    connectors = {
        "ssh": SSHConnector(),
        "winrm": WinRMConnector(),
        "aws_ssm": SSMConnector(),
        "ssm": SSMConnector(),
        "database": DatabaseConnector(),
        "api": APIConnector(),
        "network_cluster": NetworkClusterConnector(),
        "network_device": NetworkDeviceConnector(),
        "azure_bastion": AzureBastionConnector(),
        "gcp_iap": GcpIapConnector(),
        "local": LocalConnector()
    }
    
    connector = connectors.get(connector_type.lower())
    if not connector:
        raise ValueError(f"Unknown connector type: {connector_type}")
    
    return connector



