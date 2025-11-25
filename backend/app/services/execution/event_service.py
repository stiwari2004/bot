"""
Event service for publishing and listing execution events
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionEvent
from app.services.queue_client import RedisQueueClient, queue_client
from app.services import audit_log
from app.core.tracing import tracing_span

logger = get_logger(__name__)


class EventService:
    """Service for publishing and managing execution events"""
    
    def __init__(self, queue: Optional[RedisQueueClient] = None):
        self.queue = queue or queue_client
    
    async def publish_event(
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
            # Flush to ensure event is available immediately for queries
            db.flush()
            
            try:
                await audit_log.record_event(
                    session_id=session.id,
                    event_type=event_type,
                    payload=envelope,
                )
            except Exception as exc:
                logger.warning("Failed to persist audit log for session %s: %s", session.id, exc)
            
            logger.debug(
                f"Published event {event_type} for session {session.id}, step {step_number}, "
                f"stream_id={stream_id}, payload_keys={list(payload.keys())}"
            )
            return stream_id
    
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
        return await self.publish_event(
            db,
            session=session,
            event_type=event_type,
            payload=payload,
            step_number=step_number,
        )
    
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
        result = []
        for event in events:
            try:
                # event.payload is the envelope stored in DB
                # Extract the actual payload and merge with envelope fields
                envelope = event.payload if isinstance(event.payload, dict) else {}
                actual_payload = envelope.get("payload", envelope)  # Get inner payload or use envelope if no nested payload
                
                # Build response matching frontend expectations
                event_data = {
                    "id": event.id,
                    "session_id": event.session_id,
                    "step_number": event.step_number or envelope.get("step_number"),
                    "event": event.event_type or envelope.get("event"),
                    "payload": actual_payload,  # Return actual payload, not envelope
                    "stream_id": event.stream_id,
                    "created_at": (event.created_at or envelope.get("timestamp") or datetime.now(timezone.utc)).isoformat() if hasattr(event.created_at, 'isoformat') else str(event.created_at),
                    "timestamp": envelope.get("timestamp") or (event.created_at.isoformat() if event.created_at else None),
                }
                result.append(event_data)
            except Exception as e:
                logger.warning(f"Error serializing event {event.id}: {e}", exc_info=True)
                # Fallback: return basic structure
                result.append({
                    "id": event.id,
                    "session_id": event.session_id,
                    "step_number": event.step_number,
                    "event": event.event_type,
                    "payload": event.payload if isinstance(event.payload, dict) else {},
                    "stream_id": event.stream_id,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                })
        return result




