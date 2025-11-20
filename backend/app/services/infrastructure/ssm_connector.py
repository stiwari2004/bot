"""
AWS SSM connector for executing commands via boto3
"""
import asyncio
import time
from typing import Any, Dict, Optional
from app.core import metrics
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector

logger = get_logger(__name__)


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




