"""
Controller for execution endpoints - handles request/response logic
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.runbook_repository import RunbookRepository
from app.repositories.runbook_usage_repository import RunbookUsageRepository
from app.models.execution_session import ExecutionSession
from app.services.execution_orchestrator import execution_orchestrator
from app.services.idempotency import idempotency_manager
from app.services.execution import ExecutionEngine
from app.services.ticket_status_service import get_ticket_status_service
from app.core.logging import get_logger
from app.core.transactions import transaction

logger = get_logger(__name__)


class ExecutionController(BaseController):
    """Controller for execution operations"""
    
    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.execution_repo = ExecutionRepository(db)
        self.runbook_repo = RunbookRepository(db)
        self.runbook_usage_repo = RunbookUsageRepository(db)
        self.execution_engine = ExecutionEngine()
        self.ticket_status_service = get_ticket_status_service()
    
    async def create_execution_session(
        self,
        runbook_id: int,
        issue_description: Optional[str] = None,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        auto_start: bool = True
    ) -> Dict[str, Any]:
        """Create a new execution session for a runbook
        
        Args:
            runbook_id: ID of the runbook to execute
            issue_description: Optional description of the issue
            ticket_id: Optional ticket ID to associate with execution
            user_id: Optional user ID who initiated execution
            metadata: Optional metadata dictionary
            idempotency_key: Optional key for idempotent requests
            auto_start: If True, automatically start execution in background
        """
        idempotency_key = (idempotency_key or "").strip() or None
        reservation_committed = False
        
        try:
            # Verify runbook exists and is approved using repository
            runbook = self.runbook_repo.get_approved_by_id_and_tenant(
                runbook_id=runbook_id,
                tenant_id=self.tenant_id
            )
            if not runbook:
                # Check if runbook exists but not approved
                runbook = self.runbook_repo.get_by_id_and_tenant(runbook_id, self.tenant_id)
                if runbook:
                    raise self.bad_request("Runbook must be approved before execution")
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
                with transaction(self.db):
                    session = self.execution_repo.update_session(session_id=session.id, status="pending")
            
            # Update ticket status when execution starts (if ticket_id provided)
            if ticket_id:
                self.ticket_status_service.update_ticket_on_execution_start(self.db, ticket_id)
            
            # Note: Auto-start execution is now handled by the endpoint using background_tasks
            # This prevents blocking the API response while execution runs
            if auto_start and session.status == "pending":
                logger.info(f"Session {session.id} is ready for execution (will be started in background)")
                # Don't start here - let the endpoint handle it in background
            
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
        try:
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Eagerly load relationships to avoid lazy loading issues
            try:
                # Access steps to trigger loading (if not already loaded)
                _ = session.steps
            except Exception as e:
                logger.warning(f"Error loading steps for session {session_id}: {e}")
                # Continue with empty steps list
            
            try:
                runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
            except Exception as e:
                logger.warning(f"Error loading runbook for session {session_id}: {e}")
                runbook = None
            
            try:
                payload = execution_orchestrator.serialize_session(session)
            except Exception as e:
                logger.error(f"Error serializing session {session_id}: {e}", exc_info=True)
                # Return minimal payload if serialization fails
                payload = {
                    "id": session.id,
                    "tenant_id": session.tenant_id,
                    "runbook_id": session.runbook_id,
                    "status": session.status or "unknown",
                    "current_step": session.current_step,
                    "steps": [],
                    "error": "Failed to fully serialize session data"
                }
            
            if runbook:
                if runbook.is_active == "archived":
                    payload["runbook_title"] = f"{runbook.title} (Archived)"
                else:
                    payload["runbook_title"] = runbook.title
            else:
                payload["runbook_title"] = "Unknown (Runbook Deleted)"
            
            return payload
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting execution session {session_id}: {e}", exc_info=True)
            raise self.handle_error(e, f"Failed to get execution session {session_id}")
    
    def list_session_events(
        self,
        session_id: int,
        since_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return recorded execution events for a session"""
        try:
            # Verify session exists (lightweight check)
            session = self.execution_repo.get_by_id(session_id)
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Limit maximum to prevent huge queries
            if limit > 500:
                limit = 500
            if limit <= 0:
                limit = 50
            
            try:
                events = execution_orchestrator.list_events(
                    self.db,
                    session_id=session_id,
                    since_id=since_id,
                    limit=limit
                )
                return events or []  # Ensure we return a list
            except Exception as e:
                logger.error(f"Error listing events for session {session_id}: {e}", exc_info=True)
                # Return empty list instead of crashing
                return []
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in list_session_events for session {session_id}: {e}", exc_info=True)
            # Return empty list instead of crashing
            return []
    
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
                    # Refresh session from database to get latest state
                    session = self.execution_repo.get_by_id(session_id)
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
            
            # Update session progress using repository
            if approved is None or not approved or not step.requires_approval:
                remaining_steps = [s for s in session.steps if not s.completed]
                current_step = remaining_steps[0].step_number if remaining_steps else (session.steps[-1].step_number if session.steps else None)
                waiting_for_approval = any(s.requires_approval and s.approved is None for s in session.steps)
                new_status = "waiting_approval" if waiting_for_approval else ("in_progress" if session.status != "failed" else session.status)
                
                self.execution_repo.update_session(
                    session_id=session_id,
                    current_step=current_step,
                    waiting_for_approval=waiting_for_approval,
                    status=new_status
                )
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
            
            # Create runbook usage tracking using repository
            self.runbook_usage_repo.create_usage(
                runbook_id=session.runbook_id,
                tenant_id=session.tenant_id,
                user_id=session.user_id,
                issue_description=session.issue_description,
                confidence_score=0.0,
                was_helpful=was_successful,
                feedback_text=feedback_text,
                execution_time_minutes=duration_minutes
            )
            
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
            
            # Mark as abandoned using repository
            completed_at = datetime.now(timezone.utc)
            duration_minutes = None
            if session.started_at:
                duration_minutes = int((completed_at - session.started_at).total_seconds() / 60)
            
            self.execution_repo.update_session(
                session_id=session_id,
                status="abandoned",
                completed_at=completed_at,
                total_duration_minutes=duration_minutes
            )
            
            # Update ticket status if linked
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    self.db, session.ticket_id, "abandoned", issue_resolved=False
                )
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
            
            sessions = self.execution_repo.get_by_tenant(self.tenant_id, limit=limit, offset=offset)
            
            result: List[Dict[str, Any]] = []
            for session in sessions:
                try:
                    # Ensure session is attached to the current db session
                    if session not in self.db:
                        self.db.merge(session)
                    
                    payload = execution_orchestrator.serialize_session(session)
                    runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
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
    
    def get_pending_approvals(self) -> Dict[str, Any]:
        """Get all sessions waiting for approval"""
        try:
            sessions = self.execution_repo.get_pending_approvals(self.tenant_id)
            
            result = []
            for session in sessions:
                step = self.execution_repo.get_step(
                    session.id, 
                    session.approval_step_number, 
                    None  # step_type not needed for lookup
                )
                
                runbook = self.runbook_repo.get_by_id_and_tenant(session.runbook_id, self.tenant_id) if session.runbook_id else None
                
                result.append({
                    "session_id": session.id,
                    "runbook_id": session.runbook_id,
                    "runbook_title": runbook.title if runbook else "Unknown",
                    "step_number": session.approval_step_number,
                    "step_type": step.step_type if step else None,
                    "command": step.command if step else None,
                    "issue_description": session.issue_description,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                })
            
            return {"pending_approvals": result}
        except Exception as e:
            logger.exception("Failed to get pending approvals: %s", e)
            raise self.handle_error(e, "Failed to get pending approvals")


