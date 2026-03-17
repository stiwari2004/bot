"""
Execution orchestrator - CLEAN REWRITE
Coordinates execution session lifecycle and messaging
"""
import asyncio
import hashlib
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep, AgentWorkerAssignment
from app.services.execution import ExecutionEngine
from app.services.execution.queue_service import QueueService
from app.services.execution.event_service import EventService
from app.services.execution.metadata_service import MetadataService
from app.services.execution.session_serializer import SessionSerializer
from app.services.execution.orchestrator_enqueue_mixin import OrchestratorEnqueueMixin
from app.services.agent_worker_manager import agent_worker_manager
from app.services.queue_client import RedisQueueClient, queue_client

logger = get_logger(__name__)


def _run_enqueue_session_in_thread(
    runbook_id: int,
    tenant_id: int,
    ticket_id: Optional[int],
    issue_description: str,
    user_id: Optional[int],
    metadata: Optional[Dict[str, Any]],
    idempotency_key: Optional[str],
) -> int:
    """
    Run the entire enqueue_session in a dedicated thread with its own event loop.
    Keeps all sync DB and async Redis work off the main event loop.
    Returns the new session id.
    """
    import asyncio as _asyncio
    db = SessionLocal()
    try:
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            from app.services.queue_client import RedisQueueClient
            thread_queue = RedisQueueClient()
            orchestrator = ExecutionOrchestrator(queue=thread_queue)
            session = loop.run_until_complete(
                orchestrator._enqueue_session_impl(
                    db=db,
                    runbook_id=runbook_id,
                    tenant_id=tenant_id,
                    ticket_id=ticket_id,
                    issue_description=issue_description or None,
                    user_id=user_id,
                    metadata=metadata,
                    idempotency_key=idempotency_key,
                )
            )
            return session.id
        finally:
            loop.close()
    finally:
        db.close()


class ExecutionOrchestrator(OrchestratorEnqueueMixin):
    """Coordinates execution session lifecycle and messaging"""

    def __init__(self, queue: Optional[RedisQueueClient] = None) -> None:
        self.queue = queue or queue_client
        self.engine = ExecutionEngine()
        self.queue_service = QueueService(queue=self.queue)
        self.event_service = EventService(queue=self.queue)
        self.metadata_service = MetadataService()
        self.serializer = SessionSerializer(self.metadata_service)

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
        """Create a session, persist orchestration metadata, and queue assignment"""
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
            return session

        loop = asyncio.get_event_loop()
        session_id = await loop.run_in_executor(
            None,
            _run_enqueue_session_in_thread,
            runbook_id,
            tenant_id,
            ticket_id,
            issue_description or "",
            user_id,
            metadata,
            idempotency_key,
        )
        session = (
            db.query(ExecutionSession)
            .options(joinedload(ExecutionSession.steps))
            .filter(ExecutionSession.id == session_id)
            .first()
        )
        if not session:
            raise RuntimeError(f"Session {session_id} not found after enqueue")
        return session

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
        """Queue a manual command for a session"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError("Execution session not found")
        return await self.queue_service.submit_manual_command(
            db, session=session, command=command, shell=shell, run_as=run_as,
            reason=reason, timeout_seconds=timeout_seconds, user_id=user_id,
            idempotency_key=idempotency_key,
        )

    async def control_session(
        self,
        db: Session,
        *,
        session_id: int,
        action: str,
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ExecutionSession:
        """Perform pause/resume/rollback control actions"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError("Execution session not found")

        previous_status = session.status
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
            assignment_metadata = self._latest_assignment_metadata(session)
            if assignment_metadata:
                prepared_metadata = self.metadata_service.prepare_metadata(
                    db=db, tenant_id=session.tenant_id, metadata=assignment_metadata,
                )
                rollback_payload = {
                    "session_id": session.id,
                    "action": "rollback",
                    "reason": reason,
                    "user_id": user_id,
                    "metadata": prepared_metadata,
                    "connection": prepared_metadata.get("connection") or prepared_metadata,
                }
                self._persist_assignment_metadata(db, session, prepared_metadata)
                rollback_key_source = f"rollback:{session.id}:{reason or ''}:{user_id or ''}"
                rollback_idempotency = hashlib.sha256(rollback_key_source.encode("utf-8")).hexdigest()
                rollback_payload["idempotency_key"] = rollback_idempotency
                await self.queue.publish(
                    settings.REDIS_STREAM_COMMAND,
                    rollback_payload,
                    idempotency_key=rollback_idempotency,
                )
        else:
            raise ValueError(f"Unsupported action '{action}'")

        session.status = new_status
        payload = {
            "session_id": session.id,
            "previous_status": previous_status,
            "status": new_status,
            "reason": reason,
            "user_id": user_id,
        }

        await self.event_service.publish_event(db, session=session, event_type=event_type, payload=payload)
        db.commit()
        db.refresh(session)
        return session

    def list_events(
        self, db: Session, session_id: int, *, since_id: Optional[int] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return serialized execution events for a session"""
        return self.event_service.list_events(db, session_id, since_id=since_id, limit=limit)

    async def record_event(
        self, db: Session, session_id: int, *, event_type: str, payload: Dict[str, Any], step_number: Optional[int] = None,
    ) -> str:
        """Public API for recording events originating from workers"""
        return await self.event_service.record_event(db, session_id, event_type=event_type, payload=payload, step_number=step_number)

    def serialize_session(self, session: ExecutionSession) -> Dict[str, Any]:
        """Delegate to SessionSerializer"""
        return self.serializer.serialize_session(session)

    def _latest_assignment_metadata(self, session: ExecutionSession) -> Dict[str, Any]:
        """Delegate to SessionSerializer"""
        return self.serializer._latest_assignment_metadata(session)

    def _persist_assignment_metadata(self, db: Session, session: ExecutionSession, metadata: Dict[str, Any]) -> None:
        """Persist assignment metadata"""
        if not session.assignments:
            return
        latest_assignment = max(session.assignments, key=lambda item: item.id)
        latest_assignment.details = metadata
        db.add(latest_assignment)


# Create singleton instance
execution_orchestrator = ExecutionOrchestrator()
