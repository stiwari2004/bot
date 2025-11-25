"""
Execution orchestrator - CLEAN REWRITE
Coordinates execution session lifecycle and messaging
"""
import hashlib
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep, AgentWorkerAssignment
from app.services.execution import ExecutionEngine
from app.services.execution.queue_service import QueueService
from app.services.execution.event_service import EventService
from app.services.execution.metadata_service import MetadataService
from app.services.agent_worker_manager import agent_worker_manager
from app.services.policy import validate_sandbox_profile
from app.services.queue_client import RedisQueueClient, queue_client

logger = get_logger(__name__)


class ExecutionOrchestrator:
    """Coordinates execution session lifecycle and messaging"""
    
    def __init__(self, queue: Optional[RedisQueueClient] = None) -> None:
        self.queue = queue or queue_client
        self.engine = ExecutionEngine()
        self.queue_service = QueueService(queue=self.queue)
        self.event_service = EventService(queue=self.queue)
        self.metadata_service = MetadataService()
    
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
        # If worker orchestration disabled, just create session
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
        
        # Create session
        session = await self.engine.create_execution_session(
            db=db,
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            issue_description=issue_description,
            user_id=user_id,
        )
        db.refresh(session)
        
        # Validate sandbox profile
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
        
        # Update session status
        session.status = "queued"
        session.transport_channel = "redis"
        session.assignment_retry_count = 0
        session.sandbox_profile = session.sandbox_profile or "default"
        db.add(session)
        
        # Prepare metadata
        request_metadata = metadata or {}
        if request_metadata:
            session.issue_description = session.issue_description or request_metadata.get("issue_description")
        
        prepared_metadata = self.metadata_service.prepare_metadata(
            db=db,
            tenant_id=tenant_id,
            metadata=request_metadata,
        )
        sanitized_metadata = self.metadata_service.sanitize_metadata(prepared_metadata)
        if idempotency_key:
            prepared_metadata["idempotency_key"] = idempotency_key
            sanitized_metadata["idempotency_key"] = idempotency_key
        
        # Create assignment record
        assignment = AgentWorkerAssignment(
            session_id=session.id,
            status="pending",
            attempt=0,
            worker_id="unassigned",
            details=prepared_metadata,
        )
        db.add(assignment)
        db.flush()
        
        # Publish session.created event
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
        
        # Publish assignment
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
        assign_stream_id = await self.queue_service.publish_assignment(
            db,
            session,
            assign_payload,
            assignment_idempotency,
        )
        
        session.last_event_seq = assign_stream_id
        
        # Publish queued event
        await self.event_service.publish_event(
            db,
            session=session,
            event_type="session.queued",
            payload={
                "session_id": session.id,
                "stream_id": assign_stream_id,
                "status": "queued",
                "metadata": sanitized_metadata,
                "idempotency_key": idempotency_key,
            },
        )
        
        # Publish policy events
        await self.event_service.publish_event(
            db,
            session=session,
            event_type="session.policy",
            payload={
                "profile": session.sandbox_profile,
                "sla_minutes": policy_info.get("default_sla_minutes"),
            },
        )
        
        if any(step.requires_approval for step in session.steps):
            await self.event_service.publish_event(
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
        agent_worker_manager.cleanup_stale_workers()
        
        logger.info(f"Queued execution session {session.id}")
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
            db,
            session=session,
            command=command,
            shell=shell,
            run_as=run_as,
            reason=reason,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
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
                    db=db,
                    tenant_id=session.tenant_id,
                    metadata=assignment_metadata,
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
        
        await self.event_service.publish_event(
            db,
            session=session,
            event_type=event_type,
            payload=payload,
        )
        
        db.commit()
        db.refresh(session)
        return session
    
    def list_events(
        self,
        db: Session,
        session_id: int,
        *,
        since_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return serialized execution events for a session"""
        return self.event_service.list_events(db, session_id, since_id=since_id, limit=limit)
    
    async def record_event(
        self,
        db: Session,
        session_id: int,
        *,
        event_type: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
    ) -> str:
        """Public API for recording events originating from workers"""
        return await self.event_service.record_event(
            db,
            session_id,
            event_type=event_type,
            payload=payload,
            step_number=step_number,
        )
    
    def serialize_session(self, session: ExecutionSession) -> Dict[str, Any]:
        """Helper to transform ExecutionSession into response payload"""
        def serialize_step(step: ExecutionStep) -> Dict[str, Any]:
            try:
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
            except Exception as e:
                logger.warning(f"Error serializing step {step.id if step else 'unknown'}: {e}")
                return {
                    "id": step.id if step else None,
                    "step_number": step.step_number if step else 0,
                    "error": "Failed to serialize step"
                }
        
        try:
            # Safely access steps relationship
            steps_list = []
            try:
                if hasattr(session, 'steps') and session.steps:
                    steps_list = [serialize_step(step) for step in sorted(session.steps, key=lambda s: s.step_number)]
            except Exception as e:
                logger.warning(f"Error accessing steps for session {session.id}: {e}")
                steps_list = []
        except Exception as e:
            logger.warning(f"Error processing steps for session {session.id}: {e}")
            steps_list = []
        
        payload = {
            "id": session.id,
            "tenant_id": session.tenant_id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "status": session.status or "unknown",
            "current_step": session.current_step,
            "waiting_for_approval": session.waiting_for_approval or False,
            "transport_channel": session.transport_channel,
            "last_event_seq": session.last_event_seq,
            "sandbox_profile": session.sandbox_profile,
            "assignment_retry_count": session.assignment_retry_count or 0,
            "issue_description": session.issue_description,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_duration_minutes": session.total_duration_minutes,
            "steps": steps_list,
        }
        
        try:
            metadata = self._latest_assignment_metadata(session)
            if metadata:
                sanitized_metadata = self.metadata_service.sanitize_metadata(metadata)
                payload["connection"] = sanitized_metadata.get("connection") or sanitized_metadata
        except Exception as e:
            logger.warning(f"Error getting assignment metadata for session {session.id}: {e}")
        
        return payload
    
    def _latest_assignment_metadata(self, session: ExecutionSession) -> Dict[str, Any]:
        """Return the most recent assignment metadata/details for the session"""
        try:
            if not hasattr(session, 'assignments') or not session.assignments:
                return {}
            for assignment in sorted(session.assignments, key=lambda a: a.id, reverse=True):
                if assignment and hasattr(assignment, 'details') and assignment.details:
                    return assignment.details
            return {}
        except Exception as e:
            logger.warning(f"Error accessing assignment metadata: {e}")
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


# Create singleton instance
execution_orchestrator = ExecutionOrchestrator()
