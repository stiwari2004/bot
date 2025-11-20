"""
Main execution engine that orchestrates all execution services
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

from app.services.execution.session_service import SessionService
from app.services.execution.step_execution_service import StepExecutionService
from app.services.execution.approval_service import ApprovalService
from app.services.execution.rollback_service import RollbackService
from app.services.execution.connection_service import ConnectionService
from app.services.ticket_status_service import get_ticket_status_service
from app.services.resolution_verification_service import get_resolution_verification_service

logger = get_logger(__name__)


class ExecutionEngine:
    """Execute runbooks with human validation checkpoints"""
    
    def __init__(self):
        self.ticket_status_service = get_ticket_status_service()
        self.resolution_verification_service = get_resolution_verification_service()
        
        # Initialize services
        self.session_service = SessionService()
        self.connection_service = ConnectionService()
        self.rollback_service = RollbackService(self.connection_service)
        self.step_execution_service = StepExecutionService(
            self.connection_service,
            self.rollback_service,
            self.ticket_status_service,
            self.resolution_verification_service
        )
        self.approval_service = ApprovalService(
            self.step_execution_service,
            self.ticket_status_service,
            self.resolution_verification_service
        )
    
    async def create_execution_session(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int,
        ticket_id: Optional[int] = None,
        issue_description: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> ExecutionSession:
        """Create a new execution session"""
        return await self.session_service.create_execution_session(
            db=db,
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            issue_description=issue_description,
            user_id=user_id
        )
    
    async def approve_step(
        self,
        db: Session,
        session_id: int,
        step_number: int,
        user_id: Optional[int],
        approve: bool
    ) -> ExecutionSession:
        """Approve or reject a step"""
        return await self.approval_service.approve_step(
            db=db,
            session_id=session_id,
            step_number=step_number,
            user_id=user_id,
            approve=approve
        )
    
    async def start_execution(
        self,
        db: Session,
        session_id: int
    ) -> ExecutionSession:
        """Start execution (if no approval needed)"""
        logger.info(f"[START_EXECUTION] Starting execution for session {session_id}")
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        if session.status != "pending":
            logger.warning(f"[START_EXECUTION] Session {session_id} has status '{session.status}', expected 'pending'")
            raise ValueError(f"Session {session_id} is not in pending status")
        
        # Get first step
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            logger.error(f"[START_EXECUTION] No first step found for session {session_id}")
            session.status = "failed"
            db.commit()
            return session
        
        logger.info(f"[START_EXECUTION] First step found: step_number={first_step.step_number}, requires_approval={first_step.requires_approval}, command={first_step.command[:50] if first_step.command else 'N/A'}...")
        
        if first_step.requires_approval:
            # First step requires approval - wait for it
            session.status = "waiting_approval"
            session.waiting_for_approval = True
            session.approval_step_number = 1
            session.current_step = 1
            logger.info(f"[START_EXECUTION] First step requires approval. Waiting for approval...")
        else:
            # Auto-execute first step
            session.status = "in_progress"
            session.current_step = 1
            logger.info(f"[START_EXECUTION] First step does not require approval. Auto-executing...")
            await self.step_execution_service.execute_step(db, session, first_step)
        
        db.commit()
        db.refresh(session)
        return session


