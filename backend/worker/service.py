"""
Asynchronous worker service that consumes assignments and reports execution events.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core import metrics
from app.core.config import settings
from app.services.queue_client import RedisQueueClient
from app.services.infrastructure_connectors import get_connector
from app.services.idempotency import idempotency_manager
from app.core.tracing import tracing_span

logger = logging.getLogger("worker.service")
logging.basicConfig(level=os.getenv("WORKER_LOG_LEVEL", "INFO"))


class WorkerService:
    """Redis Streams-based worker that acknowledges assignments and emits execution events."""

    def __init__(
        self,
        worker_id: str,
        backend_base_url: str,
        redis_url: Optional[str] = None,
    ) -> None:
        self.worker_id = worker_id
        self.backend_base_url = backend_base_url.rstrip("/")
        self.queue = RedisQueueClient(redis_url=redis_url or settings.REDIS_URL)
        self._http_client = httpx.AsyncClient(base_url=self.backend_base_url, timeout=30.0)
        self._running = False
        self._heartbeat_interval = int(os.getenv("WORKER_HEARTBEAT_INTERVAL", "15"))
        self._last_assignment_id: Optional[int] = None
        self._current_load: int = 0
        self._session_connections: Dict[int, Dict[str, Any]] = {}
        self._cluster_sessions: Dict[str, Dict[str, Any]] = {}

    async def run(self) -> None:
        """Register worker then begin polling assignment stream."""
        await self.register()
        self._running = True

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        assignment_task = asyncio.create_task(self._process_assignments())
        command_task = asyncio.create_task(self._process_commands())
        try:
            await asyncio.wait(
                {assignment_task, command_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )
        finally:
            self._running = False
            heartbeat_task.cancel()
            with contextlib.suppress(Exception):
                await heartbeat_task
            for task in (assignment_task, command_task):
                task.cancel()
                with contextlib.suppress(Exception):
                    await task
            await self._http_client.aclose()
            await self.queue.close()

    async def register(self) -> None:
        payload = {
            "worker_id": self.worker_id,
            "capabilities": os.getenv(
                "WORKER_CAPABILITIES",
                "ssh,winrm,network_cluster,network_device,azure_bastion,gcp_iap",
            ).split(","),
            "network_segment": os.getenv("WORKER_NETWORK_SEGMENT"),
            "environment": os.getenv("WORKER_ENVIRONMENT", "dev"),
            "max_concurrency": int(os.getenv("WORKER_MAX_CONCURRENCY", "1")),
            "metadata": {"hostname": os.getenv("HOSTNAME")},
        }
        resp = await self._http_client.post("/api/v1/agent/workers/register", json=payload)
        resp.raise_for_status()
        logger.info("Registered worker %s", self.worker_id)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await self._http_client.post(
                    "/api/v1/agent/workers/heartbeat",
                    json={"worker_id": self.worker_id, "current_load": self._current_load},
                )
            except Exception as exc:
                logger.warning("Heartbeat failed: %s", exc)
            await asyncio.sleep(self._heartbeat_interval)

    async def _process_assignments(self) -> None:
        last_id = "0-0"
        while self._running:
            try:
                messages = await self.queue.read_stream(
                    settings.REDIS_STREAM_ASSIGN,
                    last_id=last_id,
                    count=10,
                    block=5_000,
                )
            except Exception as exc:
                logger.error("Error reading assignment stream: %s", exc)
                await asyncio.sleep(1)
                continue

            if not messages:
                await asyncio.sleep(0.1)
                continue

            for message_id, payload in messages:
                last_id = message_id
                session_id = payload.get("session_id")
                assignment_id = payload.get("assignment_id")
                if not session_id:
                    logger.warning("Received assignment without session_id: %s", payload)
                    continue
                with tracing_span(
                    "worker.assignment.dispatch",
                    {"session_id": session_id, "assignment_id": assignment_id},
                ):
                    try:
                        await self._handle_assignment(session_id, assignment_id, payload)
                    except Exception as exc:
                        logger.error(
                            "Failed processing assignment session_id=%s assignment_id=%s error=%s",
                            session_id,
                            assignment_id,
                            exc,
                        )
                        await self._send_dead_letter(
                            session_id=session_id,
                            reason=str(exc),
                            payload={**payload, "stream_id": message_id, "assignment_id": assignment_id},
                        )

    async def _handle_assignment(
        self,
        session_id: int,
        assignment_id: Optional[int],
        payload: Dict[str, Any],
    ) -> None:
        with tracing_span(
            "worker.assignment",
            {"session_id": session_id, "assignment_id": assignment_id},
        ):
            logger.info(
                "Handling assignment session_id=%s assignment_id=%s",
                session_id,
                assignment_id,
            )
            ack_response = await self._acknowledge_assignment(session_id, assignment_id)
            if ack_response:
                self._last_assignment_id = ack_response["assignment_id"]
                await self._publish_event(
                    session_id,
                    event="worker.assignment_acknowledged",
                    payload={"worker_id": self.worker_id, **ack_response},
                )

            metadata = (payload.get("metadata") or {}) if isinstance(payload.get("metadata"), dict) else {}
            self._session_connections[session_id] = metadata
            connector_type, connection_config = self._resolve_connector(metadata)
            cluster_meta = connection_config.get("cluster") or metadata.get("cluster") or {}
            target_host = connection_config.get("host") or connection_config.get("instance_id")
            sanitized_metadata = self._sanitize_metadata(metadata)
            steps: List[Dict[str, Any]] = payload.get("steps", [])

            await self._publish_event(
                session_id,
                event="worker.assignment_received",
                payload=self._compact_dict(
                    {
                        "worker_id": self.worker_id,
                        "assignment_id": assignment_id,
                        "step_count": len(steps),
                        "metadata": sanitized_metadata or None,
                    }
                ),
            )

            if not target_host:
                await self._publish_event(
                    session_id,
                    event="agent.connection_failed",
                    payload={
                        "worker_id": self.worker_id,
                        "reason": "Missing target host for assignment.",
                        "metadata": sanitized_metadata or None,
                    },
                )
                return

            if connector_type == "network_device":
                cluster_ready = await self._ensure_cluster_session(cluster_meta or {}, session_id)
                if not cluster_ready:
                    return
            elif connector_type == "network_cluster":
                await self._ensure_cluster_session(cluster_meta or {}, session_id)

            connection_payload = self._compact_dict(
                {
                    "worker_id": self.worker_id,
                    "host": target_host,
                    "environment": connection_config.get("environment"),
                    "connector_type": connector_type,
                    "credential_source": metadata.get("credential_source") or metadata.get("credential_provider"),
                    "metadata": sanitized_metadata or None,
                }
            )
            await self._publish_event(
                session_id,
                event="agent.connection_established",
                payload=connection_payload,
            )

            if not steps:
                await self._publish_event(
                    session_id,
                    event="worker.assignment_empty",
                    payload={"worker_id": self.worker_id},
                )
                return

            self._current_load = 1
            try:
                for step in steps:
                    step_number = step.get("step_number")
                    command_text = (step.get("command") or "").strip()
                    await self._publish_event(
                        session_id,
                        event="execution.step.started",
                        payload={
                            "worker_id": self.worker_id,
                            "step": step,
                            "connector_type": connector_type,
                        },
                        step_number=step_number,
                    )

                    result = await self._execute_connector_command(
                        connector_type,
                        command_text,
                        connection_config,
                        timeout=step.get("timeout_seconds"),
                    )

                    output_text = (result.get("output") or "").strip()
                    if output_text:
                        await self._publish_event(
                            session_id,
                            event="execution.step.output",
                            payload=self._compact_dict(
                                {
                                    "worker_id": self.worker_id,
                                    "connector_type": connector_type,
                                    "output": output_text,
                                    "metadata": sanitized_metadata or None,
                                }
                            ),
                            step_number=step_number,
                        )

                    completion_payload = self._compact_dict(
                        {
                            "worker_id": self.worker_id,
                            "success": bool(result.get("success")),
                            "exit_code": result.get("exit_code"),
                            "detail": result.get("error"),
                            "duration_ms": result.get("duration_ms"),
                            "metadata": sanitized_metadata or None,
                            "connector_type": connector_type,
                            "retry_count": result.get("retry_count"),
                        }
                    )
                    await self._publish_event(
                        session_id,
                        event="execution.step.completed",
                        payload=completion_payload,
                        step_number=step_number,
                    )

                    if not result.get("success"):
                        if result.get("connection_error"):
                            await self._publish_event(
                                session_id,
                                event="agent.connection_failed",
                                payload=self._compact_dict(
                                    {
                                        "worker_id": self.worker_id,
                                        "reason": result.get("error") or "Connector reported failure.",
                                        "metadata": sanitized_metadata or None,
                                    }
                                ),
                            )
                        break
            finally:
                self._current_load = 0

            await self._publish_event(
                session_id,
                event="session.worker_complete",
                payload={"worker_id": self.worker_id},
            )

    async def _acknowledge_assignment(
        self,
        session_id: int,
        assignment_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        body = {
            "session_id": session_id,
            "worker_id": self.worker_id,
            "assignment_id": assignment_id,
        }
        try:
            resp = await self._http_client.post("/api/v1/agent/workers/assignments/ack", json=body)
            if resp.status_code == 404:
                logger.warning("Assignment not found for session_id=%s", session_id)
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("Failed to acknowledge assignment: %s", exc)
            return None

    async def _publish_event(
        self,
        session_id: int,
        event: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
    ) -> None:
        body = {
            "session_id": session_id,
            "event": event,
            "payload": payload,
            "step_number": step_number,
        }
        try:
            resp = await self._http_client.post("/api/v1/agent/workers/events", json=body)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to publish event %s for session %s: %s", event, session_id, exc)

    async def _process_commands(self) -> None:
        last_id = "0-0"
        while self._running:
            try:
                messages = await self.queue.read_stream(
                    settings.REDIS_STREAM_COMMAND,
                    last_id=last_id,
                    count=20,
                    block=5_000,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Error reading command stream: %s", exc)
                await asyncio.sleep(1)
                continue

            if not messages:
                await asyncio.sleep(0.1)
                continue

            for message_id, payload in messages:
                last_id = message_id
                session_id = payload.get("session_id")
                if not session_id:
                    logger.warning("Received command without session_id: %s", payload)
                    continue
                with tracing_span(
                    "worker.command.dispatch",
                    {"session_id": session_id, "stream_id": message_id},
                ):
                    try:
                        await self._handle_command(session_id, payload, message_id)
                    except Exception as exc:
                        logger.error(
                            "Failed processing manual command session_id=%s: %s",
                            session_id,
                            exc,
                        )
                        await self._send_dead_letter(
                            session_id=session_id,
                            reason=str(exc),
                            payload={**payload, "stream_id": message_id},
                        )

    async def _handle_command(
        self,
        session_id: int,
        payload: Dict[str, Any],
        stream_id: str,
    ) -> None:
        idempotency_key = payload.get("idempotency_key")
        release_idempotency = False
        if idempotency_key:
            existing = await idempotency_manager.reserve("command-exec", idempotency_key)
            if existing:
                logger.info(
                    "Skipping duplicate command for session_id=%s key=%s (existing=%s)",
                    session_id,
                    idempotency_key,
                    existing,
                )
                return
            release_idempotency = True

        command_text = (payload.get("command") or "").strip()
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        if not metadata:
            metadata = self._session_connections.get(session_id, {})
        connector_type, connection_config = self._resolve_connector(metadata)
        sanitized_metadata = self._sanitize_metadata(metadata)
        cluster_meta = connection_config.get("cluster") or metadata.get("cluster") or {}

        if connector_type == "network_device":
            cluster_ready = await self._ensure_cluster_session(cluster_meta or {}, session_id)
            if not cluster_ready:
                failure_payload = self._compact_dict(
                    {
                        "worker_id": self.worker_id,
                        "command": command_text,
                        "reason": "Cluster session unavailable",
                        "metadata": sanitized_metadata or None,
                        "connector_type": connector_type,
                        "idempotency_key": idempotency_key,
                    }
                )
                await self._publish_event(
                    session_id,
                    event="session.command.failed",
                    payload=failure_payload,
                )
                return

        try:
            result = await self._execute_connector_command(
                connector_type,
                command_text,
                connection_config,
                timeout=payload.get("timeout_seconds"),
            )

            base_payload = self._compact_dict(
                {
                    "worker_id": self.worker_id,
                    "command": command_text,
                    "reason": payload.get("reason"),
                    "shell": payload.get("shell"),
                    "run_as": payload.get("run_as"),
                    "stream_id": stream_id,
                    "metadata": sanitized_metadata or None,
                    "connection": (sanitized_metadata.get("connection") if sanitized_metadata else None),
                    "connector_type": connector_type,
                    "idempotency_key": idempotency_key,
                }
            )

            if result.get("success"):
                event_payload = self._compact_dict(
                    {
                        **base_payload,
                        "message": payload.get("message") or "Manual command completed",
                        "output": result.get("output"),
                        "exit_code": result.get("exit_code"),
                        "duration_ms": result.get("duration_ms"),
                        "retry_count": result.get("retry_count"),
                    }
                )
                await self._publish_event(
                    session_id,
                    event="session.command.completed",
                    payload=event_payload,
                )
            else:
                event_payload = self._compact_dict(
                    {
                        **base_payload,
                        "error": result.get("error") or "Manual command failed",
                        "output": result.get("output"),
                        "exit_code": result.get("exit_code"),
                        "duration_ms": result.get("duration_ms"),
                        "retry_count": result.get("retry_count"),
                    }
                )
                await self._publish_event(
                    session_id,
                    event="session.command.failed",
                    payload=event_payload,
                )
                if result.get("connection_error"):
                    await self._publish_event(
                        session_id,
                        event="agent.connection_failed",
                        payload=self._compact_dict(
                            {
                                "worker_id": self.worker_id,
                                "reason": result.get("error") or "Manual command connection failure",
                                "metadata": sanitized_metadata or None,
                            }
                        ),
                    )

            status_value = "success" if result.get("success") else "failure"
            if idempotency_key:
                await idempotency_manager.commit("command-exec", idempotency_key, f"{stream_id}:{status_value}")
                release_idempotency = False
        except Exception as exc:
            logger.error("Error executing manual command: %s", exc, exc_info=True)
            failure_payload = self._compact_dict(
                {
                    "worker_id": self.worker_id,
                    "command": command_text,
                    "error": str(exc),
                    "stream_id": stream_id,
                    "metadata": sanitized_metadata or None,
                    "idempotency_key": idempotency_key,
                }
            )
            await self._publish_event(
                session_id,
                event="session.command.failed",
                payload=failure_payload,
            )
            await self._send_dead_letter(
                session_id=session_id,
                reason=str(exc),
                payload={**payload, "stream_id": stream_id},
            )
            raise
        finally:
            if release_idempotency and idempotency_key:
                await idempotency_manager.release("command-exec", idempotency_key)

    async def _send_dead_letter(
        self,
        *,
        session_id: Optional[int],
        reason: str,
        payload: Dict[str, Any],
    ) -> None:
        dead_letter_payload = {
            "session_id": session_id,
            "worker_id": self.worker_id,
            "reason": reason,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self.queue.publish(
                settings.REDIS_STREAM_DEAD_LETTER,
                dead_letter_payload,
                approximate=False,
            )
        except Exception as exc:
            logger.error("Failed to write dead-letter entry: %s", exc)

    async def _ensure_cluster_session(
        self,
        cluster_metadata: Dict[str, Any],
        session_id: int,
    ) -> bool:
        """Ensure a network cluster session is active before touching downstream devices."""
        if not cluster_metadata:
            return True
        cluster_id = cluster_metadata.get("id") or cluster_metadata.get("cluster_id")
        if not cluster_id:
            return True
        if cluster_id in self._cluster_sessions:
            return True

        timeout_seconds = int(cluster_metadata.get("timeout_seconds") or 30)
        result = await self._execute_connector_command(
            "network_cluster",
            "establish",
            {"cluster": cluster_metadata},
            timeout=timeout_seconds,
        )
        if result.get("success"):
            self._cluster_sessions[cluster_id] = {
                "metadata": cluster_metadata,
                "session_id": session_id,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._publish_event(
                session_id,
                event="agent.cluster_established",
                payload=self._compact_dict(
                    {
                        "worker_id": self.worker_id,
                        "cluster_id": cluster_id,
                        "metadata": self._sanitize_metadata({"cluster": cluster_metadata}).get("cluster"),
                    }
                ),
            )
            return True

        await self._publish_event(
            session_id,
            event="agent.connection_failed",
            payload=self._compact_dict(
                {
                    "worker_id": self.worker_id,
                    "cluster_id": cluster_id,
                    "reason": result.get("error") or "Failed to establish cluster session",
                    "metadata": self._sanitize_metadata({"cluster": cluster_metadata}).get("cluster"),
                }
            ),
        )
        return False

    def _resolve_connector(self, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        metadata = metadata or {}
        connection = metadata.get("connection") or {}
        target = metadata.get("target") or {}
        credentials = metadata.get("credentials") or metadata.get("credential") or {}
        cluster_meta = (
            metadata.get("cluster")
            or connection.get("cluster")
            or target.get("cluster")
            or {}
        )
        device_meta = (
            metadata.get("device")
            or connection.get("device")
            or target.get("device")
            or {}
        )

        connector_type = (
            metadata.get("connector_type")
            or connection.get("type")
            or metadata.get("connection_type")
            or "ssh"
        ).lower()

        host = (
            connection.get("host")
            or target.get("host")
            or metadata.get("host")
            or cluster_meta.get("management_host")
            or device_meta.get("mgmt_ip")
            or device_meta.get("host")
        )
        config = {
            "host": host,
            "port": connection.get("port") or metadata.get("port"),
            "transport": connection.get("transport"),
            "use_ssl": connection.get("use_ssl"),
            "environment": metadata.get("environment") or target.get("environment"),
            "service": metadata.get("service") or target.get("service"),
            "credential_source": metadata.get("credential_source"),
            "username": credentials.get("username"),
            "password": credentials.get("password"),
            "domain": credentials.get("domain"),
            "private_key": credentials.get("private_key"),
            "instance_id": connection.get("instance_id") or target.get("instance_id"),
            "region": connection.get("region") or target.get("region"),
            "shell": metadata.get("shell") or connection.get("shell") or ("powershell" if connector_type == "winrm" else "bash"),
            "timeout": metadata.get("timeout_seconds"),
            "cluster": cluster_meta or None,
            "device": device_meta or None,
            "resource_id": connection.get("resource_id") or metadata.get("resource_id"),
            "bastion_host": connection.get("bastion_host") or metadata.get("bastion_host"),
            "target_host": connection.get("target_host") or target.get("host"),
            "project_id": connection.get("project_id") or metadata.get("project_id"),
            "zone": connection.get("zone") or metadata.get("zone"),
            "instance_name": connection.get("instance_name") or metadata.get("instance_name"),
        }
        return connector_type, self._compact_dict(config)

    async def _execute_connector_command(
        self,
        connector_type: str,
        command: str,
        connection_config: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        start = loop.time()
        try:
            connector = get_connector(connector_type)
        except ValueError as exc:
            logger.error("Unsupported connector %s: %s", connector_type, exc)
            return {
                "success": False,
                "output": "",
                "error": f"Unsupported connector '{connector_type}'",
                "exit_code": -1,
                "connection_error": True,
                "duration_ms": int((loop.time() - start) * 1000),
            }

        try:
            result = await connector.execute_command(
                command,
                connection_config,
                timeout=timeout or int(os.getenv("WORKER_COMMAND_TIMEOUT", "60")),
            )
        except Exception as exc:
            logger.error(
                "Connector execution failure connector=%s host=%s error=%s",
                connector_type,
                connection_config.get("host"),
                exc,
            )
            result = {
                "success": False,
                "output": "",
                "error": str(exc),
                "exit_code": -1,
                "connection_error": True,
            }

        duration_ms = int((loop.time() - start) * 1000)
        if not isinstance(result, dict):
            result = {
                "success": False,
                "output": "",
                "error": "Connector returned invalid response",
                "exit_code": -1,
                "connection_error": True,
            }
        result.setdefault("exit_code", 0 if result.get("success") else 1)
        if timeout:
            result.setdefault("timeout", timeout)
        if "duration_ms" not in result or result["duration_ms"] is None:
            result["duration_ms"] = duration_ms
        if result.get("connection_error") is None:
            result["connection_error"] = False
        result.setdefault("retry_count", 0)

        telemetry_status = (
            "success"
            if result.get("success")
            else ("connection_error" if result.get("connection_error") else "failure")
        )
        metrics.record_connector_result(connector_type, telemetry_status)
        metrics.observe_connector_latency(connector_type, result["duration_ms"] / 1000.0)

        return result

    async def _send_dead_letter(
        self,
        *,
        session_id: int,
        reason: str,
        payload: Dict[str, Any],
    ) -> None:
        try:
            await self.queue.publish(
                settings.REDIS_STREAM_DEAD_LETTER,
                {
                    "session_id": session_id,
                    "reason": reason,
                    "payload": payload,
                    "worker_id": self.worker_id,
                },
            )
        except Exception as exc:
            logger.error("Failed to publish dead-letter message: %s", exc)

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if not metadata:
            return {}
        sensitive_exact = {
            "password",
            "secret",
            "token",
            "api_key",
            "access_key",
            "secret_key",
            "session_token",
            "private_key",
            "client_secret",
            "ssh_key",
            "key_material",
            "tls_key",
            "encryption_key",
            "key",
            "passphrase",
        }
        sensitive_fragments = ("password", "secret", "token", "passphrase")

        def is_sensitive(key: str) -> bool:
            key_lower = key.lower()
            if key_lower in sensitive_exact:
                return True
            return any(fragment in key_lower for fragment in sensitive_fragments)

        def sanitize(value: Any) -> Any:
            if isinstance(value, dict):
                redacted: Dict[str, Any] = {}
                for key, item in value.items():
                    if is_sensitive(key):
                        redacted[key] = "***"
                    else:
                        redacted[key] = sanitize(item)
                return redacted
            if isinstance(value, list):
                return [sanitize(item) for item in value]
            return value

        return sanitize(metadata.copy())

    def _compact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in data.items() if value not in (None, "", [], {})}


