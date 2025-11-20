"""
Queue service for execution session queue management
"""
import hashlib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionEvent
from app.services.queue_client import RedisQueueClient, queue_client
from app.services.execution.event_service import EventService
from app.services.execution.metadata_service import MetadataService

logger = get_logger(__name__)


class QueueService:
    """Service for managing execution session queues"""
    
    def __init__(self, queue: Optional[RedisQueueClient] = None):
        self.queue = queue or queue_client
        self.event_service = EventService(queue=self.queue)
        self.metadata_service = MetadataService()
    
    async def publish_assignment(
        self,
        db: Session,
        session: ExecutionSession,
        assignment_payload: Dict[str, Any],
        assignment_idempotency: str
    ) -> str:
        """Publish assignment to queue"""
        assign_stream_id = await self.queue.publish(
            settings.REDIS_STREAM_ASSIGN,
            assignment_payload,
            idempotency_key=assignment_idempotency,
        )
        return assign_stream_id
    
    async def submit_manual_command(
        self,
        db: Session,
        *,
        session: ExecutionSession,
        command: str,
        shell: Optional[str] = None,
        run_as: Optional[str] = None,
        reason: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queue a manual command for a session and emit tracking event."""
        command_payload = {
            "session_id": session.id,
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
            prepared_metadata = self.metadata_service.prepare_metadata(
                db=db,
                tenant_id=session.tenant_id,
                metadata=assignment_metadata,
            )
            connection_info = prepared_metadata.get("connection") or prepared_metadata
            command_payload["metadata"] = prepared_metadata
            command_payload["connection"] = connection_info
            sanitized_metadata = self.metadata_service.sanitize_metadata(prepared_metadata)
            self._persist_assignment_metadata(db, session, prepared_metadata)
        
        command_idempotency = idempotency_key or self._command_idempotency_key(
            session_id=session.id,
            command_payload=command_payload,
        )
        command_payload["idempotency_key"] = command_idempotency
        
        stream_id = await self.queue.publish(
            settings.REDIS_STREAM_COMMAND,
            command_payload,
            idempotency_key=command_idempotency,
        )
        
        event_payload = {
            "session_id": session.id,
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
        
        await self.event_service.publish_event(
            db,
            session=session,
            event_type="session.command.requested",
            payload=event_payload,
        )
        
        db.commit()
        
        event = (
            db.query(ExecutionEvent)
            .filter(ExecutionEvent.session_id == session.id)
            .order_by(ExecutionEvent.id.desc())
            .first()
        )
        if not event:
            raise RuntimeError("Failed to persist manual command event")
        
        db.refresh(session)
        return {
            "id": event.id,
            "session_id": session.id,
            "event": event.event_type,
            "payload": event.payload,
            "stream_id": event.stream_id,
            "created_at": event.created_at.isoformat(),
            "step_number": event.step_number,
        }
    
    def _latest_assignment_metadata(self, session: ExecutionSession) -> Dict[str, Any]:
        """Return the most recent assignment metadata/details for the session."""
        if not session.assignments:
            return {}
        for assignment in sorted(session.assignments, key=lambda a: a.id, reverse=True):
            if assignment.details:
                return assignment.details
        return {}
    
    def _persist_assignment_metadata(
        self,
        db: Session,
        session: ExecutionSession,
        metadata: Dict[str, Any],
    ) -> None:
        """Persist assignment metadata"""
        if not session.assignments:
            return
        latest_assignment = max(session.assignments, key=lambda item: item.id)
        latest_assignment.details = metadata
        db.add(latest_assignment)
    
    @staticmethod
    def _command_idempotency_key(
        *,
        session_id: int,
        command_payload: Dict[str, Any],
    ) -> str:
        """Generate idempotency key for command"""
        components = [
            str(session_id),
            command_payload.get("command") or "",
            command_payload.get("shell") or "",
            command_payload.get("run_as") or "",
            command_payload.get("reason") or "",
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

