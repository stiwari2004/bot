"""
Handles precheck analysis and processing after precheck steps complete
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.services.precheck_analysis_service import get_precheck_analysis_service
from app.services.ticketing_integration_service import get_ticketing_integration_service
from sqlalchemy.orm.attributes import flag_modified
import json
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepPrecheckHandler:
    """Handles precheck analysis and processing"""
    
    def __init__(self):
        self.precheck_service = get_precheck_analysis_service()
        self.ticketing_service = get_ticketing_integration_service()
    
    async def check_all_prechecks_complete(
        self,
        db: Session,
        session: ExecutionSession
    ) -> bool:
        """
        Check if all precheck steps are complete.
        
        Args:
            db: Database session
            session: Execution session
            
        Returns:
            True if all prechecks are complete, False otherwise
        """
        precheck_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.step_type == "precheck"
        ).order_by(ExecutionStep.step_number).all()
        
        if not precheck_steps:
            logger.debug(f"No precheck steps found for session {session.id}")
            return False
        
        all_complete = all(step.completed for step in precheck_steps)
        step_statuses = [(s.step_number, s.completed, s.success) for s in precheck_steps]
        
        logger.info(
            f"Precheck completion check for session {session.id}: "
            f"total={len(precheck_steps)}, all_complete={all_complete}, "
            f"step_statuses={step_statuses}"
        )
        
        return all_complete
    
    async def analyze_and_handle_prechecks(
        self,
        db: Session,
        session: ExecutionSession
    ) -> Optional[str]:
        """
        Analyze precheck outputs and handle the result.
        Returns 'stop' if execution should stop, None if execution should continue.
        
        Args:
            db: Database session
            session: Execution session
            
        Returns:
            'stop' if execution should stop, None if execution should continue
        """
        if not session.ticket_id:
            return None
        
        ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
        if not ticket:
            return None
        
        runbook = None
        if session.runbook_id:
            runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        
        # Analyze precheck outputs
        analysis_result = await self.precheck_service.analyze_precheck_outputs(
            db=db,
            ticket=ticket,
            session=session,
            runbook=runbook
        )
        
        analysis_status = analysis_result.get("analysis_status", "success")
        is_false_positive = analysis_result.get("is_false_positive", False)
        confidence = analysis_result.get("confidence", 0.0)
        reasoning = analysis_result.get("reasoning", "")
        
        # Store analysis result
        ticket.precheck_analysis_result = analysis_result
        ticket.precheck_executed_at = datetime.now(timezone.utc)
        ticket.precheck_status = analysis_status
        
        # Preserve meta_data
        preserved_meta = self._preserve_metadata(ticket)
        
        # Handle different scenarios
        if analysis_status == "failed":
            return await self._handle_precheck_failed(db, session, ticket, reasoning, preserved_meta)
        elif analysis_status == "ambiguous":
            return await self._handle_precheck_ambiguous(db, session, ticket, reasoning, preserved_meta)
        elif is_false_positive and confidence >= 0.7:
            return await self._handle_false_positive(db, session, ticket, reasoning, confidence, preserved_meta)
        else:
            # True positive - proceed
            ticket.status = "in_progress"
            ticket.classification = "true_positive" if not is_false_positive else "uncertain"
            ticket.meta_data = preserved_meta
            flag_modified(ticket, "meta_data")
            db.commit()
            logger.info(f"Precheck analysis: proceeding with main steps - {reasoning}")
            return None
    
    def _preserve_metadata(self, ticket: Ticket) -> Dict[str, Any]:
        """Preserve existing metadata"""
        if ticket.meta_data:
            if isinstance(ticket.meta_data, dict):
                return dict(ticket.meta_data)
            elif isinstance(ticket.meta_data, str):
                return json.loads(ticket.meta_data)
        return {}
    
    async def _handle_precheck_failed(
        self,
        db: Session,
        session: ExecutionSession,
        ticket: Ticket,
        reasoning: str,
        preserved_meta: Dict[str, Any]
    ) -> str:
        """Handle precheck execution failed scenario"""
        ticket.status = "in_progress"
        ticket.escalation_reason = f"Precheck execution failed: {reasoning}"
        ticket.meta_data = preserved_meta
        flag_modified(ticket, "meta_data")
        
        db.commit()
        db.refresh(ticket)
        
        await self.ticketing_service.mark_for_manual_review(
            db=db,
            ticket=ticket,
            reason=f"Precheck execution failed: {reasoning}"
        )
        
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Precheck execution failed, stopping: {reasoning}")
        return "stop"
    
    async def _handle_precheck_ambiguous(
        self,
        db: Session,
        session: ExecutionSession,
        ticket: Ticket,
        reasoning: str,
        preserved_meta: Dict[str, Any]
    ) -> str:
        """Handle ambiguous precheck output scenario"""
        ticket.status = "escalated"
        ticket.escalation_reason = f"Ambiguous precheck output: {reasoning}"
        ticket.meta_data = preserved_meta
        flag_modified(ticket, "meta_data")
        
        db.commit()
        db.refresh(ticket)
        
        await self.ticketing_service.escalate_ticket(
            db=db,
            ticket=ticket,
            escalation_reason=f"Ambiguous precheck output: {reasoning}"
        )
        
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Ambiguous precheck output, escalating: {reasoning}")
        return "stop"
    
    async def _handle_false_positive(
        self,
        db: Session,
        session: ExecutionSession,
        ticket: Ticket,
        reasoning: str,
        confidence: float,
        preserved_meta: Dict[str, Any]
    ) -> str:
        """Handle false positive detected scenario"""
        ticket.status = "resolved"
        ticket.classification = "false_positive"
        ticket.classification_confidence = "high" if confidence >= 0.8 else "medium"
        ticket.resolved_at = datetime.now(timezone.utc)
        ticket.meta_data = preserved_meta
        flag_modified(ticket, "meta_data")
        
        db.commit()
        db.refresh(ticket)
        
        # Update external ticket system
        external_update_success = await self.ticketing_service.resolve_ticket(
            db=db,
            ticket=ticket,
            resolution_notes=f"False positive detected: {reasoning}"
        )
        
        if external_update_success:
            logger.info(f"✅ Successfully updated external ticket {ticket.external_id} to resolved status")
        else:
            logger.warning(f"⚠️ Failed to update external ticket {ticket.external_id}")
        
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"False positive detected, resolving ticket: {reasoning}")
        return "stop"

