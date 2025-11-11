"""
Execution orchestrator responsible for queuing sessions and publishing events.
"""
from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import (
    ExecutionEvent,
    ExecutionSession,
    ExecutionStep,
    AgentWorkerAssignment,
)
from app.services.agent_worker_manager import agent_worker_manager
from app.services.credential_service import get_credential_service
from app.services.execution_engine import ExecutionEngine
from app.services.queue_client import RedisQueueClient, queue_client
from app.services.policy import validate_sandbox_profile
from app.services import audit_log
from app.core import metrics
from app.core.tracing import tracing_span

logger = get_logger(__name__)


class ExecutionOrchestrator:
    """Coordinates execution session lifecycle and messaging."""

    def __init__(self, queue: Optional[RedisQueueClient] = None) -> None:
        self.queue = queue or queue_client
        self.engine = ExecutionEngine()
        self.credential_service = get_credential_service()

    async def enqueue_session(
        self,
        db: Session,
        *,
        runbook_id: int,
        tenant_id: int,
        ticket_id: Optional[int] = None,
        issue_description: Optional[str] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> ExecutionSession:
        """Create a session, persist orchestration metadata, and queue assignment."""
        if not settings.WORKER_ORCHESTRATION_ENABLED:
            session = await self.engine.create_execution_session(
                db=db,
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                issue_description=issue_description,
                user_id=user_id,
            )
            db.refresh(session)
            logger.warning(
                "Worker orchestration disabled; returning session without queuing (session_id=%s)",
                session.id,
            )
            return session

        with tracing_span(
            "execution.enqueue_session",
            {"runbook_id": runbook_id, "tenant_id": tenant_id, "ticket_id": ticket_id},
        ):
            session = await self.engine.create_execution_session(
                db=db,
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                issue_description=issue_description,
                user_id=user_id,
            )

            # Refresh session with relationships for later serialization
            db.refresh(session)

            policy_info = validate_sandbox_profile(
                session.sandbox_profile or "default",
                steps=[
                    {
                        "step_number": step.step_number,
                        "blast_radius": step.blast_radius,
                        "severity": step.approval_policy,
                    }
                    for step in session.steps
                ],
                context={"tenant_id": tenant_id},
            )

            previous_state = session.status or "unknown"
            session.status = "queued"
            session.transport_channel = "redis"
            session.assignment_retry_count = 0
            session.sandbox_profile = session.sandbox_profile or "default"
            db.add(session)

            metrics.record_assignment("queued")
            if previous_state != session.status:
                metrics.record_state_transition(previous_state, session.status)

            request_metadata = metadata or {}
            if request_metadata:
                session.issue_description = session.issue_description or request_metadata.get("issue_description")

            prepared_metadata = self._prepare_metadata(
                db=db,
                tenant_id=tenant_id,
                metadata=request_metadata,
            )
            sanitized_metadata = self._sanitize_metadata(prepared_metadata)
            if idempotency_key:
                prepared_metadata["idempotency_key"] = idempotency_key
                sanitized_metadata["idempotency_key"] = idempotency_key

            # Create pending assignment record (worker chosen later)
            assignment = AgentWorkerAssignment(
                session_id=session.id,
                status="pending",
                attempt=0,
                worker_id="unassigned",
                details=prepared_metadata,
            )
            db.add(assignment)
            db.flush()

            # Publish events
            created_payload = {
                "session_id": session.id,
                "runbook_id": runbook_id,
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "status": session.status,
                "metadata": sanitized_metadata,
                "idempotency_key": idempotency_key,
            }
            await self._publish_event(
                db,
                session=session,
                event_type="session.created",
                payload=created_payload,
            )

            steps_payload = [
                {
                    "step_id": step.id,
                    "step_number": step.step_number,
                    "step_type": step.step_type,
                    "requires_approval": step.requires_approval,
                    "sandbox_profile": step.sandbox_profile,
                    "blast_radius": step.blast_radius,
                    "command": step.command,
                    "rollback_command": step.rollback_command,
                }
                for step in session.steps
            ]

            assign_payload = {
                "session_id": session.id,
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "runbook_id": runbook_id,
                "steps": steps_payload,
                "sandbox_profile": session.sandbox_profile,
                "metadata": prepared_metadata,
                "attempt": session.assignment_retry_count,
                "assignment_id": assignment.id,
                "policy": {
                    "profile": session.sandbox_profile,
                    "sla_minutes": policy_info.get("default_sla_minutes"),
                },
                "idempotency_key": idempotency_key,
            }

            assignment_idempotency = f"assignment:{session.id}:{assignment.id}"
            assign_stream_id = await self.queue.publish(
                settings.REDIS_STREAM_ASSIGN,
                assign_payload,
                idempotency_key=assignment_idempotency,
            )

            session.last_event_seq = assign_stream_id
            queued_event_payload = {
                "session_id": session.id,
                "stream_id": assign_stream_id,
                "status": "queued",
                "metadata": sanitized_metadata,
                "idempotency_key": idempotency_key,
            }
            await self._publish_event(
                db,
                session=session,
                event_type="session.queued",
                payload=queued_event_payload,
            )

            await self._publish_event(
                db,
                session=session,
                event_type="session.policy",
                payload={
                    "profile": session.sandbox_profile,
                    "sla_minutes": policy_info.get("default_sla_minutes"),
                },
            )

            if any(step.requires_approval for step in session.steps):
                await self._publish_event(
                    db,
                    session=session,
                    event_type="approval.policy",
                    payload={
                        "mode": "per_step",
                        "sla_minutes": policy_info.get("default_sla_minutes"),
                    },
                )

            db.commit()
            db.refresh(session)

            logger.info(
                "Queued execution session %s (runbook=%s tenant=%s)",
                session.id,
                runbook_id,
                tenant_id,
            )

            # Touch worker manager to cleanup stale entries periodically
            agent_worker_manager.cleanup_stale_workers()

            return session

    def _prepare_metadata(
        self,
        *,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return metadata enriched with resolved credentials while avoiding mutation."""
        if not metadata:
            return {}

        prepared = copy.deepcopy(metadata)
        if prepared.get("credentials") and not prepared.get("credential_source"):
            prepared["credential_source"] = "inline"

        credential_source = prepared.get("credential_source")
        if isinstance(credential_source, str) and credential_source.strip():
            prepared = self._apply_credential_source(db, tenant_id, prepared, credential_source)

        return prepared

    def _apply_credential_source(
        self,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
        credential_source: str,
    ) -> Dict[str, Any]:
        source = credential_source.strip()
        lower_source = source.lower()

        if lower_source.startswith("alias:"):
            alias_reference = source.split(":", 1)[1].strip()
            if not alias_reference:
                raise ValueError("Credential alias provided but empty.")
            return self._hydrate_alias_credentials(db, tenant_id, metadata, alias_reference)

        return metadata

    def _hydrate_alias_credentials(
        self,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
        alias_reference: str,
    ) -> Dict[str, Any]:
        alias_name, alias_environment = self._parse_alias_reference(alias_reference)
        environment_hint = (
            metadata.get("environment")
            or metadata.get("target", {}).get("environment")
            or alias_environment
        )
        credential = self.credential_service.resolve_alias(
            db=db,
            tenant_id=tenant_id,
            alias=alias_name,
            environment=environment_hint,
        )
        if not credential:
            raise ValueError(f"Credential alias '{alias_reference}' not found.")

        self.credential_service.log_credential_usage(
            tenant_id=tenant_id,
            alias=alias_name,
        )

        credentials_block = metadata.setdefault("credentials", {})

        def merge_if_missing(target: Dict[str, Any], key: str, value: Any) -> None:
            if value is None:
                return
            if key not in target or target[key] in (None, ""):
                target[key] = value

        merge_fields = {
            "username": credential.get("username"),
            "password": credential.get("password"),
            "api_key": credential.get("api_key"),
            "private_key": credential.get("private_key"),
            "domain": credential.get("domain"),
        }

        metadata_payload = credential.get("metadata") or {}
        for extra_key in (
            "access_key",
            "secret_key",
            "session_token",
            "client_id",
            "client_secret",
            "certificate",
            "keytab",
            "passphrase",
            "tenant",
        ):
            if extra_key not in merge_fields:
                merge_fields[extra_key] = metadata_payload.get(extra_key)

        for key, value in (credential.get("secrets") or {}).items():
            if key not in merge_fields:
                merge_fields[key] = value

        for key, value in merge_fields.items():
            merge_if_missing(credentials_block, key, value)

        metadata["credential_alias"] = credential.get("alias", alias_name)
        metadata["credential_source"] = f"alias:{credential.get('alias', alias_name)}"
        metadata.setdefault("credential_resolved", {})
        metadata["credential_resolved"].update(
            {
                "alias": credential.get("alias", alias_name),
                "type": credential.get("type"),
                "environment": credential.get("environment") or environment_hint,
                "source": credential.get("source", "alias"),
                "credential_id": credential.get("credential_id"),
            }
        )
        if credential.get("rotated_at"):
            metadata["credential_resolved"]["rotated_at"] = credential["rotated_at"]

        connection_block = metadata.setdefault("connection", {})
        merge_if_missing(connection_block, "host", credential.get("host"))
        merge_if_missing(connection_block, "port", credential.get("port"))

        target_block = metadata.setdefault("target", {})
        merge_if_missing(target_block, "host", credential.get("host"))
        merge_if_missing(target_block, "port", credential.get("port"))
        merge_if_missing(target_block, "environment", credential.get("environment"))

        return metadata

    def _parse_alias_reference(self, alias: str) -> Tuple[str, Optional[str]]:
        value = alias.strip()
        if not value:
            return "", None

        if "@" in value:
            name, environment = value.split("@", 1)
            return name.strip(), environment.strip() or None
        if "/" in value:
            environment, name = value.split("/", 1)
            return name.strip(), environment.strip() or None
        if ":" in value:
            environment, name = value.split(":", 1)
            if environment and name:
                return name.strip(), environment.strip() or None
        return value, None

    def _persist_assignment_metadata(
        self,
        db: Session,
        session: ExecutionSession,
        metadata: Dict[str, Any],
    ) -> None:
        if not session.assignments:
            return
        latest_assignment = max(session.assignments, key=lambda item: item.id)
        latest_assignment.details = metadata
        db.add(latest_assignment)

    async def _publish_event(
        self,
        db: Session,
        *,
        session: ExecutionSession,
        event_type: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
    ) -> str:
        """Persist event to database and broadcast to event stream."""
        with tracing_span(
            "execution.publish_event",
            {"session_id": session.id, "event_type": event_type},
        ):
            envelope = {
                "event": event_type,
                "session_id": session.id,
                "step_number": step_number,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            stream_id = await self.queue.publish(settings.REDIS_STREAM_EVENTS, envelope)

            event = ExecutionEvent(
                session_id=session.id,
                step_number=step_number,
                event_type=event_type,
                payload=envelope,
                stream_id=stream_id,
            )
            db.add(event)
            try:
                await audit_log.record_event(
                    session_id=session.id,
                    event_type=event_type,
                    payload=envelope,
                )
            except Exception as exc:
                logger.warning("Failed to persist audit log for session %s: %s", session.id, exc)
            return stream_id

    def list_events(
        self,
        db: Session,
        session_id: int,
        *,
        since_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return serialized execution events for a session."""
        query = (
            db.query(ExecutionEvent)
            .filter(ExecutionEvent.session_id == session_id)
            .order_by(ExecutionEvent.id.asc())
        )

        if since_id:
            query = query.filter(ExecutionEvent.id > since_id)

        events = query.limit(limit).all()
        return [
            {
                "id": event.id,
                "session_id": event.session_id,
                "step_number": event.step_number,
                "event": event.event_type,
                "payload": event.payload,
                "stream_id": event.stream_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]

    async def record_event(
        self,
        db: Session,
        session_id: int,
        *,
        event_type: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
    ) -> str:
        """Public API for recording events originating from workers."""
        session = (
            db.query(ExecutionSession)
            .filter(ExecutionSession.id == session_id)
            .first()
        )
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        stream_id = await self._publish_event(
            db,
            session=session,
            event_type=event_type,
            payload=payload,
            step_number=step_number,
        )
        return stream_id

    async def submit_manual_command(
        self,
        db: Session,
        *,
        session_id: int,
        command: str,
        shell: Optional[str] = None,
        run_as: Optional[str] = None,
        reason: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queue a manual command for a session and emit tracking event."""
        session = (
            db.query(ExecutionSession)
            .filter(ExecutionSession.id == session_id)
            .first()
        )
        if not session:
            raise ValueError("Execution session not found")

        command_payload = {
            "session_id": session_id,
            "command": command,
            "shell": shell or "bash",
            "run_as": run_as,
            "reason": reason,
            "timeout_seconds": timeout_seconds,
            "user_id": user_id,
        }
        if idempotency_key:
            command_payload["idempotency_key"] = idempotency_key

        assignment_metadata = self._latest_assignment_metadata(session)
        sanitized_metadata = {}
        if assignment_metadata:
            prepared_metadata = self._prepare_metadata(
                db=db,
                tenant_id=session.tenant_id,
                metadata=assignment_metadata,
            )
            connection_info = prepared_metadata.get("connection") or prepared_metadata
            command_payload["metadata"] = prepared_metadata
            command_payload["connection"] = connection_info
            sanitized_metadata = self._sanitize_metadata(prepared_metadata)
            self._persist_assignment_metadata(db, session, prepared_metadata)

        command_idempotency = idempotency_key or self._command_idempotency_key(
            session_id=session_id,
            command_payload=command_payload,
        )
        command_payload["idempotency_key"] = command_idempotency

        stream_id = await self.queue.publish(
            settings.REDIS_STREAM_COMMAND,
            command_payload,
            idempotency_key=command_idempotency,
        )

        event_payload = {
            "session_id": session_id,
            "command": command,
            "shell": shell or "bash",
            "run_as": run_as,
            "reason": reason,
            "timeout_seconds": timeout_seconds,
            "user_id": user_id,
            "stream_id": stream_id,
            "status": "queued",
            "idempotency_key": command_idempotency,
        }
        if sanitized_metadata:
            event_payload["metadata"] = sanitized_metadata
            event_payload["connection"] = sanitized_metadata.get("connection") or sanitized_metadata

        await self._publish_event(
            db,
            session=session,
            event_type="session.command.requested",
            payload=event_payload,
        )

        db.commit()

        event = (
            db.query(ExecutionEvent)
            .filter(ExecutionEvent.session_id == session_id)
            .order_by(ExecutionEvent.id.desc())
            .first()
        )
        if not event:
            raise RuntimeError("Failed to persist manual command event")

        db.refresh(session)
        return {
            "id": event.id,
            "session_id": session_id,
            "event": event.event_type,
            "payload": event.payload,
            "stream_id": event.stream_id,
            "created_at": event.created_at.isoformat(),
            "step_number": event.step_number,
        }

    async def control_session(
        self,
        db: Session,
        *,
        session_id: int,
        action: str,
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ExecutionSession:
        """Perform pause/resume/rollback control actions."""
        session = (
            db.query(ExecutionSession)
            .filter(ExecutionSession.id == session_id)
            .first()
        )
        if not session:
            raise ValueError("Execution session not found")

        previous_status = session.status
        payload: Dict[str, Any] = {
            "session_id": session.id,
            "previous_status": previous_status,
            "reason": reason,
            "user_id": user_id,
        }

        new_status = previous_status
        event_type = None

        if action == "pause":
            new_status = "paused"
            event_type = "session.paused"
        elif action == "resume":
            new_status = "in_progress"
            event_type = "session.resumed"
        elif action == "rollback":
            new_status = "rollback_requested"
            event_type = "session.rollback_requested"
            rollback_payload = {
                "session_id": session.id,
                "action": "rollback",
                "reason": reason,
                "user_id": user_id,
            }
            assignment_metadata = self._latest_assignment_metadata(session)
            if assignment_metadata:
                prepared_metadata = self._prepare_metadata(
                    db=db,
                    tenant_id=session.tenant_id,
                    metadata=assignment_metadata,
                )
                rollback_payload["metadata"] = prepared_metadata
                rollback_payload["connection"] = prepared_metadata.get("connection") or prepared_metadata
                self._persist_assignment_metadata(db, session, prepared_metadata)
            rollback_key_source = f"rollback:{session.id}:{reason or ''}:{user_id or ''}"
            rollback_idempotency = hashlib.sha256(rollback_key_source.encode("utf-8")).hexdigest()
            rollback_payload["idempotency_key"] = rollback_idempotency
            command_stream_id = await self.queue.publish(
                settings.REDIS_STREAM_COMMAND,
                rollback_payload,
                idempotency_key=rollback_idempotency,
            )
            payload["command_stream_id"] = command_stream_id
        else:
            raise ValueError(f"Unsupported action '{action}'")

        payload["status"] = new_status
        session.status = new_status

        if previous_status != new_status:
            metrics.record_state_transition(previous_status, new_status)

        await self._publish_event(
            db,
            session=session,
            event_type=event_type,
            payload=payload,
        )

        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def _command_idempotency_key(
        *,
        session_id: int,
        command_payload: Dict[str, Any],
    ) -> str:
        components = [
            str(session_id),
            command_payload.get("command") or "",
            command_payload.get("shell") or "",
            command_payload.get("run_as") or "",
            command_payload.get("reason") or "",
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def serialize_session(self, session: ExecutionSession) -> Dict[str, Any]:
        """Helper to transform ExecutionSession into response payload."""
        def serialize_step(step: ExecutionStep) -> Dict[str, Any]:
            return {
                "id": step.id,
                "step_number": step.step_number,
                "step_type": step.step_type,
                "command": step.command,
                "rollback_command": step.rollback_command,
                "requires_approval": step.requires_approval,
                "approved": step.approved,
                "approved_at": step.approved_at.isoformat() if step.approved_at else None,
                "sandbox_profile": step.sandbox_profile,
                "blast_radius": step.blast_radius,
                "approval_policy": step.approval_policy,
                "completed": step.completed,
                "success": step.success,
                "output": step.output,
                "notes": step.notes,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }

        payload = {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "status": session.status,
            "current_step": session.current_step,
            "waiting_for_approval": session.waiting_for_approval,
            "transport_channel": session.transport_channel,
            "last_event_seq": session.last_event_seq,
            "sandbox_profile": session.sandbox_profile,
            "assignment_retry_count": session.assignment_retry_count,
            "issue_description": session.issue_description,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": [serialize_step(step) for step in sorted(session.steps, key=lambda s: s.step_number)],
        }
        metadata = self._latest_assignment_metadata(session)
        if metadata:
            sanitized_metadata = self._sanitize_metadata(metadata)
            payload["connection"] = sanitized_metadata.get("connection") or sanitized_metadata
        return payload

    def _latest_assignment_metadata(self, session: ExecutionSession) -> Dict[str, Any]:
        """Return the most recent assignment metadata/details for the session."""
        if not session.assignments:
            return {}
        for assignment in sorted(session.assignments, key=lambda a: a.id, reverse=True):
            if assignment.details:
                return assignment.details
        return {}

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Return a redacted copy of metadata suitable for emitting to clients."""
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
                result: Dict[str, Any] = {}
                for key, item in value.items():
                    if is_sensitive(key):
                        result[key] = "***"
                    else:
                        result[key] = sanitize(item)
                return result
            if isinstance(value, list):
                return [sanitize(item) for item in value]
            return value

        return sanitize(metadata.copy())


execution_orchestrator = ExecutionOrchestrator()


