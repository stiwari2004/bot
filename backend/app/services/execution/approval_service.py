"""
Approval service for execution step approvals
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class ApprovalService:
    """Handles approval workflow for execution steps"""
    
    def __init__(self, step_execution_service, ticket_status_service, resolution_verification_service):
        self.step_execution_service = step_execution_service
        self.ticket_status_service = ticket_status_service
        self.resolution_verification_service = resolution_verification_service
    
    async def approve_step(
        self,
        db: Session,
        session_id: int,
        step_number: int,
        user_id: Optional[int],
        approve: bool
    ) -> ExecutionSession:
        """Approve or reject a step"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_number
        ).first()
        
        if not step:
            raise ValueError(f"Step {step_number} not found")
        
        if not step.requires_approval:
            raise ValueError(f"Step {step_number} does not require approval")
        
        if step.approved is not None:
            raise ValueError(f"Step {step_number} already approved/rejected")
        
        # Record approval
        step.approved = approve
        step.approved_by = user_id
        step.approved_at = datetime.utcnow()
        
        if not approve:
            # Rejected - mark session as failed
            session.status = "failed"
            session.waiting_for_approval = False
            session.completed_at = datetime.utcnow()
            
            # Update ticket status
            if session.ticket_id:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, session.ticket_id, "rejected", issue_resolved=False
                )
            
            db.commit()
            return session
        
        # Approved - continue execution
        logger.info(f"[APPROVE_STEP] Step {step_number} approved for session {session_id}. Executing step...")
        logger.info(f"[APPROVE_STEP] Step details: step_id={step.id}, command={step.command[:100] if step.command else 'N/A'}...")
        session.waiting_for_approval = False
        session.approval_step_number = None
        
        # Execute the step
        logger.info(f"[APPROVE_STEP] Calling execute_step for session {session_id}, step {step_number}")
        try:
            await self.step_execution_service.execute_step(db, session, step)
            logger.info(f"[APPROVE_STEP] execute_step completed for session {session_id}, step {step_number}")
        except Exception as e:
            logger.error(f"[APPROVE_STEP] Error in execute_step for session {session_id}, step {step_number}: {e}", exc_info=True)
            raise
        
        # Refresh session to get updated step status
        db.refresh(session)
        
        # Check if there are more steps
        next_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == step_number + 1,
            ExecutionStep.completed == False
        ).first()
        
        if next_step:
            logger.info(f"Step {step_number} completed. Found next step {next_step.step_number}")
            if next_step.requires_approval:
                session.status = "waiting_approval"
                session.waiting_for_approval = True
                session.approval_step_number = step_number + 1
                session.current_step = step_number + 1
                logger.info(f"Step {next_step.step_number} requires approval. Waiting for approval...")
            else:
                # Auto-execute next step
                session.status = "in_progress"
                session.current_step = step_number + 1
                logger.info(f"Step {next_step.step_number} does not require approval. Auto-executing...")
                await self.step_execution_service.execute_step(db, session, next_step)
        else:
            # All steps completed
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            if session.started_at:
                duration = (session.completed_at - session.started_at).total_seconds() / 60
                session.total_duration_minutes = int(duration)
            
            # Verify resolution and update ticket status
            if session.ticket_id:
                verification_result = await self.resolution_verification_service.verify_resolution(
                    db, session.id, session.ticket_id
                )
                logger.info(
                    f"Resolution verification for session {session.id}: "
                    f"resolved={verification_result['resolved']}, "
                    f"confidence={verification_result['confidence']:.2f}"
                )
            else:
                # If no ticket, just mark as completed
                pass
        
        db.commit()
        return session




