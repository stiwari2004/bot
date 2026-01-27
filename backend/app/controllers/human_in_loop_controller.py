"""
HumanInLoopController
Handles HTTP requests for human-in-the-loop workspace operations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.approval_service import ApprovalService
from app.core.logging import get_logger

logger = get_logger(__name__)


class HumanInLoopController(BaseController):
    """Controller for human-in-the-loop workspace operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        # Initialize approval service dependencies
        from app.services.execution.step_execution_service import StepExecutionService
        from app.services.ticket.ticket_status_service import TicketStatusService
        from app.services.execution.resolution_verification_service import ResolutionVerificationService
        
        step_execution_service = StepExecutionService()
        ticket_status_service = TicketStatusService()
        resolution_verification_service = ResolutionVerificationService()
        
        self.approval_service = ApprovalService(
            step_execution_service=step_execution_service,
            ticket_status_service=ticket_status_service,
            resolution_verification_service=resolution_verification_service
        )
    
    async def get_pending_approvals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all pending approvals for the tenant
        
        Returns list of execution steps waiting for approval
        """
        try:
            sessions = self.db.query(ExecutionSession).filter(
                ExecutionSession.tenant_id == self.tenant_id,
                ExecutionSession.waiting_for_approval == True,
                ExecutionSession.status == "waiting_approval"
            ).limit(limit).all()
            
            pending_approvals = []
            
            for session in sessions:
                step = self.db.query(ExecutionStep).filter(
                    ExecutionStep.session_id == session.id,
                    ExecutionStep.step_number == session.approval_step_number,
                    ExecutionStep.completed == False
                ).first()
                
                if step:
                    from app.models.runbook import Runbook
                    runbook_title = None
                    if session.runbook_id:
                        runbook = self.db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
                        if runbook:
                            runbook_title = runbook.title
                    
                    pending_approvals.append({
                        "session_id": session.id,
                        "step_id": step.id,
                        "step_number": step.step_number,
                        "runbook_id": session.runbook_id,
                        "runbook_title": runbook_title,
                        "ticket_id": session.ticket_id,
                        "command": step.command,
                        "command_payload": step.command_payload,
                        "requires_approval": step.requires_approval,
                        "waiting_since": session.created_at.isoformat() if session.created_at else None,
                        "current_parameters": step.command_payload
                    })
            
            return pending_approvals
        
        except Exception as e:
            logger.error(f"Error getting pending approvals: {e}")
            raise self.handle_error(e, "Failed to get pending approvals")
    
    async def approve_step(
        self,
        session_id: int,
        step_id: int,
        approve: bool,
        user_id: int,
        reason: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Approve or reject an execution step with optional parameter tuning
        
        Args:
            session_id: Execution session ID
            step_id: Execution step ID
            approve: Whether to approve (True) or reject (False)
            user_id: User ID making the decision
            reason: Optional reason for the decision
            parameters: Optional parameters to tune before approval
            
        Returns:
            Result dictionary
        """
        try:
            # Verify session belongs to tenant
            session = self.db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id,
                ExecutionSession.tenant_id == self.tenant_id
            ).first()
            
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Get step
            step = self.db.query(ExecutionStep).filter(
                ExecutionStep.id == step_id,
                ExecutionStep.session_id == session_id
            ).first()
            
            if not step:
                raise self.not_found("Execution step", step_id)
            
            # Tune parameters if provided
            if parameters:
                await self.approval_service.tune_parameters(
                    db=self.db,
                    session_id=session_id,
                    step_id=step_id,
                    parameters=parameters,
                    user_id=user_id,
                    reason=reason or "Parameter tuning before approval"
                )
            
            # Approve or reject step
            step_number = step.step_number
            updated_session = await self.approval_service.approve_step(
                db=self.db,
                session_id=session_id,
                step_number=step_number,
                user_id=user_id,
                approve=approve
            )
            
            return {
                "session_id": session_id,
                "step_id": step_id,
                "approved": approve,
                "status": updated_session.status,
                "message": "Step approved successfully" if approve else "Step rejected"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error approving step {step_id} in session {session_id}: {e}")
            raise self.handle_error(e, "Failed to approve step")
    
    async def tune_parameters(
        self,
        session_id: int,
        step_id: int,
        parameters: Dict[str, Any],
        user_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tune parameters for an execution step before approval
        
        Args:
            session_id: Execution session ID
            step_id: Execution step ID
            parameters: Dictionary of parameter_name -> tuned_value
            user_id: User ID making the modification
            reason: Optional reason for tuning
            
        Returns:
            Result dictionary
        """
        try:
            # Verify session belongs to tenant
            session = self.db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id,
                ExecutionSession.tenant_id == self.tenant_id
            ).first()
            
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Get step
            step = self.db.query(ExecutionStep).filter(
                ExecutionStep.id == step_id,
                ExecutionStep.session_id == session_id
            ).first()
            
            if not step:
                raise self.not_found("Execution step", step_id)
            
            # Tune parameters
            tunings = await self.approval_service.tune_parameters(
                db=self.db,
                session_id=session_id,
                step_id=step_id,
                parameters=parameters,
                user_id=user_id,
                reason=reason
            )
            
            return {
                "session_id": session_id,
                "step_id": step_id,
                "tuned_parameters": len(tunings),
                "parameters": parameters,
                "message": "Parameters tuned successfully"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error tuning parameters for step {step_id} in session {session_id}: {e}")
            raise self.handle_error(e, "Failed to tune parameters")
    
    def get_audit_trail(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get audit trail for an execution session
        
        Args:
            session_id: Execution session ID
            
        Returns:
            List of audit records
        """
        try:
            # Verify session belongs to tenant
            session = self.db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id,
                ExecutionSession.tenant_id == self.tenant_id
            ).first()
            
            if not session:
                raise self.not_found("Execution session", session_id)
            
            # Get audit trail
            audit_trail = self.approval_service.get_audit_trail(
                db=self.db,
                session_id=session_id
            )
            
            return audit_trail
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting audit trail for session {session_id}: {e}")
            raise self.handle_error(e, "Failed to get audit trail")
