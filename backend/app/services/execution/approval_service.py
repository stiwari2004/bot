"""
Approval service for execution step approvals
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.parameter_tuning import ParameterTuning
from app.models.approval_audit import ApprovalAudit
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
        
        # Record approval with timezone-aware timestamps
        step.approved = approve
        step.approved_by = user_id
        step.approved_at = datetime.now(timezone.utc)
        
        if not approve:
            # Rejected - mark session as abandoned
            session.status = "abandoned"
            session.waiting_for_approval = False
            session.completed_at = datetime.now(timezone.utc)
            
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
            session.completed_at = datetime.now(timezone.utc)
            if session.started_at:
                # Both started_at and completed_at are timezone-aware, safe to subtract
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
        
        # Create audit record
        self._create_audit_record(
            db=db,
            session_id=session_id,
            step_id=step.id,
            action="approve" if approve else "reject",
            user_id=user_id,
            reason=None,
            modified_parameters=None
        )
        
        db.commit()
        return session
    
    async def tune_parameters(
        self,
        db: Session,
        session_id: int,
        step_id: int,
        parameters: Dict[str, Any],
        user_id: Optional[int],
        reason: Optional[str] = None
    ) -> List[ParameterTuning]:
        """
        Tune/modify parameters for an execution step
        
        Args:
            db: Database session
            session_id: Execution session ID
            step_id: Execution step ID
            parameters: Dictionary of parameter_name -> tuned_value
            user_id: User ID making the modification
            reason: Optional reason for tuning
            
        Returns:
            List of ParameterTuning records created
        """
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        step = db.query(ExecutionStep).filter(ExecutionStep.id == step_id).first()
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if step.session_id != session_id:
            raise ValueError(f"Step {step_id} does not belong to session {session_id}")
        
        tunings = []
        
        # Get original parameters from step command_payload
        original_params = step.command_payload or {}
        
        for param_name, tuned_value in parameters.items():
            original_value = original_params.get(param_name)
            
            # Create parameter tuning record
            tuning = ParameterTuning(
                tenant_id=session.tenant_id,
                session_id=session_id,
                step_id=step_id,
                runbook_id=session.runbook_id,
                parameter_name=param_name,
                parameter_type=self._infer_parameter_type(tuned_value),
                original_value=str(original_value) if original_value is not None else None,
                tuned_value=str(tuned_value),
                tuned_by=user_id,
                tuned_at=datetime.now(timezone.utc),
                reason=reason
            )
            db.add(tuning)
            tunings.append(tuning)
            
            # Update step command_payload with tuned value
            if step.command_payload is None:
                step.command_payload = {}
            step.command_payload[param_name] = tuned_value
        
        # Create audit record for parameter tuning
        self._create_audit_record(
            db=db,
            session_id=session_id,
            step_id=step_id,
            action="modify",
            user_id=user_id,
            reason=reason or "Parameter tuning",
            modified_parameters=parameters,
            original_parameters=original_params
        )
        
        db.commit()
        
        logger.info(
            f"Tuned {len(tunings)} parameters for step {step_id} in session {session_id}"
        )
        
        return tunings
    
    def get_audit_trail(
        self,
        db: Session,
        session_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for an execution session
        
        Args:
            db: Database session
            session_id: Execution session ID
            
        Returns:
            List of audit records as dictionaries
        """
        audits = db.query(ApprovalAudit).filter(
            ApprovalAudit.session_id == session_id
        ).order_by(ApprovalAudit.timestamp.asc()).all()
        
        return [
            {
                "id": audit.id,
                "action": audit.action,
                "user_id": audit.user_id,
                "timestamp": audit.timestamp.isoformat() if audit.timestamp else None,
                "reason": audit.reason,
                "modified_parameters": audit.modified_parameters,
                "original_parameters": audit.original_parameters,
                "outcome": audit.outcome,
                "outcome_notes": audit.outcome_notes,
                "step_id": audit.step_id,
            }
            for audit in audits
        ]
    
    def _create_audit_record(
        self,
        db: Session,
        session_id: int,
        step_id: Optional[int],
        action: str,
        user_id: Optional[int],
        reason: Optional[str] = None,
        modified_parameters: Optional[Dict[str, Any]] = None,
        original_parameters: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ApprovalAudit:
        """Create an audit record for an approval action"""
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Execution session {session_id} not found")
        
        audit = ApprovalAudit(
            tenant_id=session.tenant_id,
            session_id=session_id,
            step_id=step_id,
            action=action,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            modified_parameters=modified_parameters,
            original_parameters=original_parameters,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(audit)
        return audit
    
    def _infer_parameter_type(self, value: Any) -> str:
        """Infer parameter type from value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, (list, dict)):
            return "json"
        else:
            return "string"




