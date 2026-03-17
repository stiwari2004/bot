"""
Mixin: _enqueue_session_impl for ExecutionOrchestrator
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, AgentWorkerAssignment
from app.services.execution.connection_service import resolve_target_connection_for_assignment
from app.services.agent_worker_manager import agent_worker_manager
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.services.policy import validate_sandbox_profile

logger = get_logger(__name__)


class OrchestratorEnqueueMixin:
    """Enqueue implementation for ExecutionOrchestrator."""

    async def _enqueue_session_impl(
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
        """Implementation of enqueue_session (used inside thread with its own db and loop)."""
        session = await self.engine.create_execution_session(
            db=db,
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            issue_description=issue_description,
            user_id=user_id,
        )
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

        session.status = "queued"
        session.transport_channel = "redis"
        session.assignment_retry_count = 0
        session.sandbox_profile = session.sandbox_profile or "default"
        db.add(session)

        tracker = SubscriptionTracker(db)
        allowed, error_msg = tracker.check_node_limit(tenant_id)
        if not allowed:
            raise ValueError(error_msg or "Node limit reached")

        request_metadata = dict(metadata or {})
        if issue_description:
            request_metadata["issue_description"] = issue_description
        if request_metadata:
            session.issue_description = session.issue_description or request_metadata.get("issue_description")
        try:
            connection = resolve_target_connection_for_assignment(db, tenant_id, ticket_id, request_metadata)
            request_metadata = dict(request_metadata)
            request_metadata["connection"] = connection
            if connection.get("credential_source") and not request_metadata.get("credential_source"):
                request_metadata["credential_source"] = connection["credential_source"]
        except ValueError as e:
            logger.warning("Target host resolution failed: %s", e)
            raise

        try:
            prepared_metadata = self.metadata_service.prepare_metadata(
                db=db, tenant_id=tenant_id, metadata=request_metadata,
            )
        except Exception as e:
            logger.warning("Credential hydration failed (worker may lack username/password): %s", e, exc_info=True)
            prepared_metadata = dict(request_metadata)

        sanitized_metadata = self.metadata_service.sanitize_metadata(prepared_metadata)
        if idempotency_key:
            prepared_metadata["idempotency_key"] = idempotency_key
            sanitized_metadata["idempotency_key"] = idempotency_key

        logger.info("Session create: credential hydration done, creating assignment record")
        assignment = AgentWorkerAssignment(
            session_id=session.id,
            status="pending",
            attempt=0,
            worker_id="unassigned",
            details=prepared_metadata,
        )
        db.add(assignment)
        db.flush()
        logger.info("Session create: assignment record flushed, publishing session.created event")

        await self.event_service.publish_event(
            db,
            session=session,
            event_type="session.created",
            payload={
                "session_id": session.id,
                "runbook_id": runbook_id,
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "status": session.status,
                "metadata": sanitized_metadata,
                "idempotency_key": idempotency_key,
            },
        )

        steps_payload = []
        for step in session.steps:
            step_dict = {
                "step_id": step.id,
                "step_number": step.step_number,
                "step_type": step.step_type,
                "requires_approval": step.requires_approval,
                "sandbox_profile": step.sandbox_profile,
                "blast_radius": step.blast_radius,
                "command": step.command,
                "rollback_command": step.rollback_command,
            }
            if step.command_payload and isinstance(step.command_payload, dict):
                to_sec = step.command_payload.get("timeout_seconds")
                if to_sec is not None:
                    try:
                        step_dict["timeout_seconds"] = int(to_sec)
                    except (TypeError, ValueError):
                        pass
            steps_payload.append(step_dict)

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
        logger.info("Session create: publishing assignment to Redis (session_id=%s)", session.id)
        assign_stream_id = await self.queue_service.publish_assignment(
            db, session, assign_payload, assignment_idempotency,
        )
        logger.info("Session create: assignment published, stream_id=%s", assign_stream_id)
        session.last_event_seq = assign_stream_id

        await self.event_service.publish_event(
            db, session=session, event_type="session.queued",
            payload={
                "session_id": session.id,
                "stream_id": assign_stream_id,
                "status": "queued",
                "metadata": sanitized_metadata,
                "idempotency_key": idempotency_key,
            },
        )

        await self.event_service.publish_event(
            db, session=session, event_type="session.policy",
            payload={
                "profile": session.sandbox_profile,
                "sla_minutes": policy_info.get("default_sla_minutes"),
            },
        )

        if any(step.requires_approval for step in session.steps):
            await self.event_service.publish_event(
                db, session=session, event_type="approval.policy",
                payload={
                    "mode": "per_step",
                    "sla_minutes": policy_info.get("default_sla_minutes"),
                },
            )

        db.commit()
        db.refresh(session)
        agent_worker_manager.cleanup_stale_workers()

        logger.info(f"Queued execution session {session.id}")
        return session
