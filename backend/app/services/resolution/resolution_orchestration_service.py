"""
ResolutionOrchestrationService
Orchestrates complete resolution flow from ticket → execution → verification → closure
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.resolution_flow import ResolutionFlow
from app.models.execution_session import ExecutionSession
from app.repositories.resolution_flow_repository import ResolutionFlowRepository
from app.services.resolution_verification_service import ResolutionVerificationService
from app.services.ticket_status_service import get_ticket_status_service

logger = get_logger(__name__)


class ResolutionOrchestrationService:
    """Service for orchestrating end-to-end resolution workflows"""
    
    def __init__(self):
        self.resolution_verification_service = ResolutionVerificationService()
        self.ticket_status_service = get_ticket_status_service()
    
    async def create_resolution_flow(
        self,
        db: Session,
        ticket_id: int,
        tenant_id: int,
        runbook_id: Optional[int] = None,
        auto_resolution_enabled: bool = False,
        confidence_threshold: float = 0.8,
        max_iterations: int = 3
    ) -> ResolutionFlow:
        """
        Create a new resolution flow for a ticket
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            tenant_id: Tenant ID
            runbook_id: Runbook ID (optional)
            auto_resolution_enabled: Whether to auto-resolve on high confidence
            confidence_threshold: Confidence threshold for auto-resolution
            max_iterations: Maximum number of resolution attempts
            
        Returns:
            Created ResolutionFlow object
        """
        # Check if flow already exists
        repo = ResolutionFlowRepository(db)
        existing = repo.get_by_ticket(ticket_id, tenant_id)
        
        if existing and existing.workflow_status == 'in_progress':
            logger.info(f"Resolution flow already exists for ticket {ticket_id}")
            return existing
        
        # Create new flow
        flow = ResolutionFlow(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            runbook_id=runbook_id,
            current_phase='precheck',
            workflow_status='in_progress',
            auto_resolution_enabled='true' if auto_resolution_enabled else 'false',
            confidence_threshold=confidence_threshold,
            max_iterations=max_iterations,
            iteration_number=1,
        )
        
        db.add(flow)
        db.commit()
        db.refresh(flow)
        
        logger.info(f"Created resolution flow {flow.id} for ticket {ticket_id}")
        return flow
    
    async def advance_phase(
        self,
        db: Session,
        flow_id: int,
        new_phase: str,
        phase_data: Optional[Dict[str, Any]] = None
    ) -> ResolutionFlow:
        """
        Advance resolution flow to next phase
        
        Args:
            db: Database session
            flow_id: Flow ID
            new_phase: New phase ('precheck', 'fix', 'verification', 'closure', 'escalated')
            phase_data: Optional data for the phase
            
        Returns:
            Updated ResolutionFlow
        """
        repo = ResolutionFlowRepository(db)
        flow = repo.get(flow_id)
        
        if not flow:
            raise ValueError(f"Resolution flow {flow_id} not found")
        
        # Update phase and store phase data
        flow.current_phase = new_phase
        
        if phase_data:
            if new_phase == 'precheck':
                flow.precheck_results = phase_data
            elif new_phase == 'fix':
                flow.fix_results = phase_data
            elif new_phase == 'verification':
                flow.verification_results = phase_data
            elif new_phase == 'closure':
                flow.closure_data = phase_data
        
        db.add(flow)
        db.commit()
        db.refresh(flow)
        
        logger.info(f"Advanced flow {flow_id} to phase: {new_phase}")
        return flow
    
    async def auto_resolve_ticket(
        self,
        db: Session,
        ticket_id: int,
        tenant_id: int,
        runbook_id: int,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Automatically resolve a ticket with high confidence
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            tenant_id: Tenant ID
            runbook_id: Runbook ID to execute
            confidence: Confidence score for auto-resolution
            
        Returns:
            Resolution result
        """
        # Get or create flow
        repo = ResolutionFlowRepository(db)
        flow = repo.get_by_ticket(ticket_id, tenant_id)
        
        if not flow:
            flow = await self.create_resolution_flow(
                db, ticket_id, tenant_id, runbook_id,
                auto_resolution_enabled=True,
                confidence_threshold=0.8
            )
        
        # Check if confidence meets threshold
        if confidence < float(flow.confidence_threshold or 0.8):
            return {
                "auto_resolved": False,
                "reason": f"Confidence {confidence:.2f} below threshold {flow.confidence_threshold}",
                "flow_id": flow.id,
            }
        
        # Store decision confidence
        flow.decision_confidence = confidence
        flow.current_phase = 'fix'
        flow.runbook_id = runbook_id
        
        db.add(flow)
        db.commit()
        
        # Note: Actual execution would be triggered separately
        # This method just sets up the flow for auto-resolution
        
        return {
            "auto_resolved": True,
            "flow_id": flow.id,
            "confidence": confidence,
            "runbook_id": runbook_id,
            "message": "Flow created for auto-resolution",
        }
    
    async def complete_resolution_flow(
        self,
        db: Session,
        flow_id: int,
        success: bool,
        verification_result: Optional[Dict[str, Any]] = None
    ) -> ResolutionFlow:
        """
        Complete a resolution flow
        
        Args:
            db: Database session
            flow_id: Flow ID
            success: Whether resolution was successful
            verification_result: Optional verification result data
            
        Returns:
            Updated ResolutionFlow
        """
        repo = ResolutionFlowRepository(db)
        flow = repo.get(flow_id)
        
        if not flow:
            raise ValueError(f"Resolution flow {flow_id} not found")
        
        if success:
            flow.workflow_status = 'completed'
            flow.current_phase = 'closure'
            flow.completed_at = datetime.now(timezone.utc)
            
            if verification_result:
                flow.verification_results = verification_result
            
            # Update ticket status
            self.ticket_status_service.update_ticket_on_execution_complete(
                db, flow.ticket_id, "completed", issue_resolved=True
            )
        else:
            # Check if we should retry or escalate
            if flow.iteration_number >= flow.max_iterations:
                flow.workflow_status = 'escalated'
                flow.current_phase = 'escalated'
                flow.escalated_at = datetime.now(timezone.utc)
                flow.escalated_reason = f"Failed after {flow.iteration_number} iterations"
                
                # Update ticket status
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, flow.ticket_id, "failed", issue_resolved=False
                )
            else:
                # Retry - increment iteration
                flow.iteration_number += 1
                flow.current_phase = 'precheck'  # Start over
                flow.workflow_status = 'in_progress'
        
        db.add(flow)
        db.commit()
        db.refresh(flow)
        
        logger.info(
            f"Completed resolution flow {flow_id}: "
            f"success={success}, status={flow.workflow_status}"
        )
        
        return flow
    
    async def get_flow_status(
        self,
        db: Session,
        flow_id: int
    ) -> Dict[str, Any]:
        """
        Get current status of a resolution flow
        
        Args:
            db: Database session
            flow_id: Flow ID
            
        Returns:
            Flow status dictionary
        """
        repo = ResolutionFlowRepository(db)
        flow = repo.get(flow_id)
        
        if not flow:
            raise ValueError(f"Resolution flow {flow_id} not found")
        
        return {
            "flow_id": flow.id,
            "ticket_id": flow.ticket_id,
            "current_phase": flow.current_phase,
            "workflow_status": flow.workflow_status,
            "iteration_number": flow.iteration_number,
            "max_iterations": flow.max_iterations,
            "auto_resolution_enabled": flow.auto_resolution_enabled == 'true',
            "decision_confidence": float(flow.decision_confidence) if flow.decision_confidence else None,
            "execution_session_id": flow.execution_session_id,
            "runbook_id": flow.runbook_id,
            "started_at": flow.started_at.isoformat() if flow.started_at else None,
            "completed_at": flow.completed_at.isoformat() if flow.completed_at else None,
            "escalated_at": flow.escalated_at.isoformat() if flow.escalated_at else None,
            "escalated_reason": flow.escalated_reason,
        }

