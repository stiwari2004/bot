"""
Main execution engine - CLEAN REWRITE
Simple orchestrator for execution services
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

from app.services.execution.session_service import SessionService
from app.services.execution.step_execution_service import StepExecutionService
from app.services.execution.approval_service import ApprovalService
from app.services.execution.rollback_service import RollbackService
from app.services.execution.connection_service import ConnectionService
from app.services.execution.event_service import EventService
from app.services.ticket_status_service import get_ticket_status_service
from app.services.resolution_verification_service import get_resolution_verification_service
from app.services.precheck_analysis_service import get_precheck_analysis_service
from app.services.ticketing_integration_service import get_ticketing_integration_service
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from datetime import datetime, timezone

logger = get_logger(__name__)


class ExecutionEngine:
    """Execute runbooks with human validation checkpoints"""
    
    def __init__(self):
        self.ticket_status_service = get_ticket_status_service()
        self.resolution_verification_service = get_resolution_verification_service()
        self.precheck_analysis_service = get_precheck_analysis_service()
        self.ticketing_integration_service = get_ticketing_integration_service()
        
        # Initialize services
        self.event_service = EventService()
        self.session_service = SessionService()
        self.connection_service = ConnectionService()
        self.rollback_service = RollbackService(self.connection_service)
        self.step_execution_service = StepExecutionService(
            self.connection_service,
            self.rollback_service,
            self.ticket_status_service,
            self.resolution_verification_service,
            event_service=self.event_service
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
        logger.info(f"Starting execution for session {session_id}")
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        if session.status != "pending":
            raise ValueError(f"Session {session_id} is not in pending status")
        
        # Get first step
        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id,
            ExecutionStep.step_number == 1
        ).first()
        
        if not first_step:
            logger.error(f"No first step found for session {session_id}")
            session.status = "failed"
            db.commit()
            return session
        
        if first_step.requires_approval:
            # First step requires approval - wait for it
            session.status = "waiting_approval"
            session.waiting_for_approval = True
            session.approval_step_number = 1
            session.current_step = 1
            logger.info(f"First step requires approval. Waiting...")
        else:
            # Auto-execute first step
            session.status = "in_progress"
            session.started_at = datetime.now(timezone.utc)
            session.current_step = 1
            db.commit()
            db.refresh(session)
            
            # Execute first step
            try:
                await self.step_execution_service.execute_step(db, session, first_step)
            except Exception as e:
                logger.error(f"Error executing step {first_step.step_number}: {e}", exc_info=True)
                raise
        
        db.commit()
        db.refresh(session)
        return session
    
    async def analyze_prechecks_and_decide(
        self,
        db: Session,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Analyze precheck outputs and decide whether to proceed with main steps
        
        Args:
            db: Database session
            session_id: Execution session ID
            
        Returns:
            {
                "proceed": bool,
                "reason": str,
                "analysis_result": Dict
            }
        """
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise ValueError(f"Execution session {session_id} not found")
            
            if not session.ticket_id:
                logger.info(f"Session {session_id} has no ticket, proceeding with execution")
                return {
                    "proceed": True,
                    "reason": "No ticket associated with session",
                    "analysis_result": {}
                }
            
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {session.ticket_id} not found")
                return {
                    "proceed": True,
                    "reason": "Ticket not found, proceeding anyway",
                    "analysis_result": {}
                }
            
            # Get runbook
            runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
            
            # Analyze precheck outputs
            analysis_result = await self.precheck_analysis_service.analyze_precheck_outputs(
                db=db,
                ticket=ticket,
                session=session,
                runbook=runbook
            )
            
            # Store analysis result in ticket
            ticket.precheck_analysis_result = analysis_result
            ticket.precheck_executed_at = datetime.now(timezone.utc)
            ticket.precheck_status = analysis_result.get("analysis_status", "success")
            
            analysis_status = analysis_result.get("analysis_status", "success")
            is_false_positive = analysis_result.get("is_false_positive", False)
            confidence = analysis_result.get("confidence", 0.0)
            reasoning = analysis_result.get("reasoning", "")
            
            # Handle different scenarios
            if analysis_status == "failed":
                # Precheck execution failed - mark for manual review
                ticket.status = "in_progress"
                ticket.escalation_reason = f"Precheck execution failed: {reasoning}"
                db.commit()
                
                # Update external ticket
                await self.ticketing_integration_service.mark_for_manual_review(
                    db=db,
                    ticket=ticket,
                    reason=f"Precheck execution failed: {reasoning}"
                )
                
                return {
                    "proceed": False,
                    "reason": f"Precheck execution failed: {reasoning}",
                    "analysis_result": analysis_result
                }
            
            elif analysis_status == "ambiguous":
                # Ambiguous output - escalate
                ticket.status = "escalated"
                ticket.escalation_reason = f"Ambiguous precheck output: {reasoning}"
                db.commit()
                
                # Update external ticket
                await self.ticketing_integration_service.escalate_ticket(
                    db=db,
                    ticket=ticket,
                    escalation_reason=f"Ambiguous precheck output: {reasoning}"
                )
                
                return {
                    "proceed": False,
                    "reason": f"Ambiguous precheck output: {reasoning}",
                    "analysis_result": analysis_result
                }
            
            elif is_false_positive and confidence >= 0.7:
                # False positive detected with high confidence - close ticket
                ticket.status = "closed"
                ticket.classification = "false_positive"
                ticket.classification_confidence = "high" if confidence >= 0.8 else "medium"
                ticket.resolved_at = datetime.now(timezone.utc)
                db.commit()
                
                # Update external ticket
                await self.ticketing_integration_service.close_ticket(
                    db=db,
                    ticket=ticket,
                    reason=f"False positive detected: {reasoning}"
                )
                
                # Mark session as completed (no main steps needed)
                session.status = "completed"
                session.completed_at = datetime.now(timezone.utc)
                db.commit()
                
                return {
                    "proceed": False,
                    "reason": f"False positive detected: {reasoning}",
                    "analysis_result": analysis_result
                }
            
            else:
                # True positive or uncertain - proceed with main steps
                ticket.status = "in_progress"
                ticket.classification = "true_positive" if not is_false_positive else "uncertain"
                db.commit()
                
                return {
                    "proceed": True,
                    "reason": reasoning or "Proceeding with main steps",
                    "analysis_result": analysis_result
                }
                
        except Exception as e:
            logger.error(f"Error analyzing prechecks for session {session_id}: {e}", exc_info=True)
            # On error, proceed with execution (fail-safe)
            return {
                "proceed": True,
                "reason": f"Error during precheck analysis: {str(e)}, proceeding anyway",
                "analysis_result": {}
            }
