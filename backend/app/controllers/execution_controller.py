"""
Controller for execution endpoints - handles request/response logic
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.models.execution_session import ExecutionSession, ExecutionStep, ExecutionFeedback
from app.models.runbook import Runbook
from app.models.runbook_usage import RunbookUsage
from app.services.execution_orchestrator import execution_orchestrator
from app.services.idempotency import idempotency_manager
from app.services.execution import ExecutionEngine
from app.services.ticket_status_service import get_ticket_status_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionController(BaseController):
    """Controller for execution operations"""
    
    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)
        self.execution_engine = ExecutionEngine()
        self.ticket_status_service = get_ticket_status_service()
    
    async def create_execution_session(
        self,
        runbook_id: int,
        issue_description: Optional[str] = None,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new execution session for a runbook"""
        idempotency_key = (idempotency_key or "").strip() or None
        reservation_committed = False
        
        try:
            runbook = self.db.query(Runbook).filter(Runbook.id == runbook_id).first()
            if not runbook:
                raise self.not_found("Runbook", runbook_id)
            
            if idempotency_key:
                existing_id = await idempotency_manager.reserve("session", idempotency_key)
                if existing_id:
                    if existing_id == "__PENDING__":
                        raise HTTPException(
                            status_code=409,
                            detail="Session creation already in progress for provided idempotency key."
                        )
                    existing_session = self.execution_repo.get_by_id(int(existing_id))
                    if existing_session:
                        payload = execution_orchestrator.serialize_session(existing_session)
                        payload["runbook_title"] = runbook.title
                        return payload
            
            session = await execution_orchestrator.enqueue_session(
                self.db,
                runbook_id=runbook_id,
                tenant_id=self.tenant_id,
                ticket_id=ticket_id,
                issue_description=issue_description,
                user_id=user_id,
                metadata=metadata,
                idempotency_key=idempotency_key
            )
            
            # For demo endpoint, always auto-start execution
            if session.status == "queued":
                logger.info(f"Session {session.id} is queued. Changing to pending and starting execution for demo...")
                session.status = "pending"
                self.db.commit()
                self.db.refresh(session)
            
            if session.status == "pending":
                try:
                    logger.info(f"Auto-starting execution for session {session.id}")
                    session = await self.execution_engine.start_execution(self.db, session.id)
                    self.db.refresh(session)
                    logger.info(f"Execution started for session {session.id}, status: {session.status}")
                except Exception as e:
                    logger.error(f"Failed to auto-start execution for session {session.id}: {e}", exc_info=True)
            
            payload = execution_orchestrator.serialize_session(session)
            payload["runbook_title"] = runbook.title
            
            if idempotency_key:
                await idempotency_manager.commit("session", idempotency_key, str(session.id))
                reservation_committed = True
            
            return payload
        except HTTPException:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("session", idempotency_key)
            raise
        except Exception as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("session", idempotency_key)
            self.db.rollback()
            logger.exception("Failed to enqueue execution session: %s", e)
            raise self.handle_error(e, "Failed to create execution session")
    
    def get_execution_session(self, session_id: int) -> Dict[str, Any]:
        """Get execution session details with all steps"""
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Execution session", session_id)
        
        runbook = self.db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        
        payload = execution_orchestrator.serialize_session(session)
        if runbook:
            if runbook.is_active == "archived":
                payload["runbook_title"] = f"{runbook.title} (Archived)"
            else:
                payload["runbook_title"] = runbook.title
        else:
            payload["runbook_title"] = "Unknown (Runbook Deleted)"
        
        return payload
    
    def list_session_events(
        self,
        session_id: int,
        since_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return recorded execution events for a session"""
        session = self.execution_repo.get_by_id(session_id)
        if not session:
            raise self.not_found("Execution session", session_id)
        
        events = execution_orchestrator.list_events(
            self.db,
            session_id=session_id,
            since_id=since_id,
            limit=limit
        )
        return events
    
    async def update_execution_step(
        self,
        session_id: int,
        step_number: int,
        step_type: str,
        completed: bool,
        success: Optional[bool] = None,
        output: Optional[str] = None,
        notes: Optional[str] = None,
        approved: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update a specific step's completion status"""
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            step = self.execution_repo.get_step(session_id, step_number, step_type)
            if not step:
                raise self.not_found("Execution step", step_number)
            
            # Update step
            step.completed = completed
            if success is not None:
                step.success = success
            elif not completed:
                step.success = None
            
            if output is not None:
                step.output = output
            if notes is not None:
                step.notes = notes
            
            if completed:
                step.completed_at = datetime.now(timezone.utc)
            else:
                step.completed_at = None
            
            if approved is not None:
                if approved and step.requires_approval and step.approved is None:
                    # New approval - trigger execution
                    session = await self.execution_engine.approve_step(
                        db=self.db,
                        session_id=session_id,
                        step_number=step_number,
                        user_id=None,
                        approve=True
                    )
                    self.db.refresh(session)
                    logger.info(f"Step {step_number} approved and executed. Session status: {session.status}")
                    return {"message": "Step approved and execution triggered", "session": session}
                else:
                    step.approved = approved
                    step.approved_at = datetime.now(timezone.utc) if approved else None
                    if not approved:
                        session.status = "failed"
                        session.waiting_for_approval = False
                        session.completed_at = datetime.now(timezone.utc)
            elif step.requires_approval and step.approved is None:
                session.waiting_for_approval = True
            
            # Update session progress
            if approved is None or not approved or not step.requires_approval:
                remaining_steps = [s for s in session.steps if not s.completed]
                if remaining_steps:
                    session.current_step = remaining_steps[0].step_number
                else:
                    session.current_step = session.steps[-1].step_number if session.steps else None
                session.waiting_for_approval = any(s.requires_approval and s.approved is None for s in session.steps)
                if session.waiting_for_approval:
                    session.status = "waiting_approval"
                elif session.status != "failed":
                    session.status = "in_progress"
            
            self.db.commit()
            return {"message": "Step updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise self.handle_error(e, "Failed to update step")
    
    async def submit_manual_command(
        self,
        session_id: int,
        command: str,
        shell: Optional[str] = "bash",
        run_as: Optional[str] = None,
        reason: Optional[str] = None,
        timeout_seconds: Optional[int] = 600,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a manual command to run within the execution session"""
        idempotency_key = (idempotency_key or "").strip() or None
        reservation_committed = False
        
        try:
            if idempotency_key:
                existing = await idempotency_manager.reserve("manual-command", idempotency_key)
                if existing:
                    if existing == "__PENDING__":
                        raise HTTPException(
                            status_code=409,
                            detail="Manual command processing already in progress for provided idempotency key."
                        )
                    raise HTTPException(
                        status_code=409,
                        detail="Duplicate manual command detected for provided idempotency key."
                    )
            
            event_record = await execution_orchestrator.submit_manual_command(
                self.db,
                session_id=session_id,
                command=command,
                shell=shell,
                run_as=run_as,
                reason=reason,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                idempotency_key=idempotency_key
            )
            
            if idempotency_key:
                await idempotency_manager.commit(
                    "manual-command",
                    idempotency_key,
                    event_record.get("stream_id") or ""
                )
                reservation_committed = True
            
            return event_record
        except ValueError as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("manual-command", idempotency_key)
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            if idempotency_key and not reservation_committed:
                await idempotency_manager.release("manual-command", idempotency_key)
            logger.exception("Failed to submit manual command: %s", e)
            raise self.handle_error(e, "Failed to submit manual command")
    
    async def control_execution_session(
        self,
        session_id: int,
        action: Literal["pause", "resume", "rollback"],
        reason: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Pause, resume, or request rollback for a session"""
        try:
            session = await execution_orchestrator.control_session(
                self.db,
                session_id=session_id,
                action=action,
                reason=reason,
                user_id=user_id
            )
            return execution_orchestrator.serialize_session(session)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Failed to perform session control action: %s", e)
            raise self.handle_error(e, "Failed to control session")
    
    def complete_execution_session(
        self,
        session_id: int,
        was_successful: bool,
        issue_resolved: bool,
        rating: int,
        feedback_text: Optional[str] = None,
        suggestions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete an execution session and record feedback"""
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Calculate duration
            completed_at = datetime.now()
            duration_minutes = int((completed_at - session.started_at).total_seconds() / 60) if session.started_at else 0
            
            # Update session
            session.status = "completed" if was_successful else "failed"
            session.completed_at = completed_at
            session.total_duration_minutes = duration_minutes
            
            # Create feedback
            self.execution_repo.create_feedback(
                session_id=session_id,
                was_successful=was_successful,
                issue_resolved=issue_resolved,
                rating=rating,
                feedback_text=feedback_text,
                suggestions=suggestions
            )
            
            # Create or update runbook usage tracking
            runbook_usage = RunbookUsage(
                runbook_id=session.runbook_id,
                tenant_id=session.tenant_id,
                user_id=session.user_id,
                issue_description=session.issue_description,
                confidence_score=0.0,
                was_helpful=was_successful,
                feedback_text=feedback_text,
                execution_time_minutes=duration_minutes
            )
            self.db.add(runbook_usage)
            self.db.commit()
            
            return {"message": "Execution session completed", "session_id": session_id}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise self.handle_error(e, "Failed to complete execution session")
    
    def abandon_execution_session(
        self,
        session_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Abandon a stuck execution session"""
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            if session.status in ["completed", "failed", "abandoned"]:
                raise self.bad_request(f"Session is already {session.status} and cannot be abandoned")
            
            # Mark as abandoned
            session.status = "abandoned"
            session.completed_at = datetime.now(timezone.utc)
            if session.started_at:
                duration_minutes = int((session.completed_at - session.started_at).total_seconds() / 60)
                session.total_duration_minutes = duration_minutes
            
            # Update ticket status if linked
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    self.db, session.ticket_id, "abandoned", issue_resolved=False
                )
            
            self.db.commit()
            logger.info(f"Execution session {session_id} abandoned. Reason: {reason or 'No reason provided'}")
            
            return {"message": "Execution session abandoned", "session_id": session_id}
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.exception("Failed to abandon execution session: %s", e)
            raise self.handle_error(e, "Failed to abandon execution session")
    
    def get_runbook_execution_history(self, runbook_id: int) -> Dict[str, Any]:
        """Get all execution sessions for a specific runbook"""
        sessions = self.execution_repo.get_by_runbook(runbook_id)
        
        result: List[Dict[str, Any]] = []
        for session in sessions:
            payload = execution_orchestrator.serialize_session(session)
            payload["steps_count"] = len(session.steps)
            if session.feedback:
                payload["feedback"] = {
                    "was_successful": session.feedback.was_successful,
                    "issue_resolved": session.feedback.issue_resolved,
                    "rating": session.feedback.rating,
                    "feedback_text": session.feedback.feedback_text
                }
            result.append(payload)
        
        return {"sessions": result}
    
    def list_all_executions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get all execution sessions (paginated)"""
        try:
            if limit <= 0 or limit > 500:
                limit = 50
            if offset < 0:
                offset = 0
            
            sessions = self.execution_repo.get_by_tenant(self.tenant_id, limit, offset)
            
            result: List[Dict[str, Any]] = []
            for session in sessions:
                try:
                    # Ensure session is attached to the current db session
                    if session not in self.db:
                        self.db.merge(session)
                    
                    payload = execution_orchestrator.serialize_session(session)
                    runbook = self.db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
                    if runbook:
                        if runbook.is_active == "archived":
                            payload["runbook_title"] = f"{runbook.title} (Archived)"
                        else:
                            payload["runbook_title"] = runbook.title
                    else:
                        payload["runbook_title"] = "Unknown (Runbook Deleted)"
                    result.append(payload)
                except Exception as e:
                    logger.error(f"Error serializing session {session.id}: {e}", exc_info=True)
                    # Skip problematic sessions but continue
                    continue
            
            return {"sessions": result}
        except Exception as e:
            logger.exception("Failed to list execution sessions: %s", e)
            # Return empty result instead of raising error
            return {"sessions": []}


