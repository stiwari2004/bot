"""
ResolutionController
Handles HTTP requests for resolution orchestration operations
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.services.resolution.resolution_orchestration_service import ResolutionOrchestrationService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResolutionController(BaseController):
    """Controller for resolution orchestration operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.orchestration_service = ResolutionOrchestrationService()
    
    async def create_resolution_flow(
        self,
        ticket_id: int,
        runbook_id: Optional[int] = None,
        auto_resolution_enabled: bool = False,
        confidence_threshold: float = 0.8,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Create a resolution flow for a ticket
        
        Args:
            ticket_id: Ticket ID
            runbook_id: Runbook ID (optional)
            auto_resolution_enabled: Whether to auto-resolve on high confidence
            confidence_threshold: Confidence threshold for auto-resolution
            max_iterations: Maximum number of resolution attempts
            
        Returns:
            Created flow information
        """
        try:
            flow = await self.orchestration_service.create_resolution_flow(
                db=self.db,
                ticket_id=ticket_id,
                tenant_id=self.tenant_id,
                runbook_id=runbook_id,
                auto_resolution_enabled=auto_resolution_enabled,
                confidence_threshold=confidence_threshold,
                max_iterations=max_iterations
            )
            
            return {
                "flow_id": flow.id,
                "ticket_id": flow.ticket_id,
                "current_phase": flow.current_phase,
                "workflow_status": flow.workflow_status,
                "auto_resolution_enabled": flow.auto_resolution_enabled == 'true',
                "message": "Resolution flow created successfully"
            }
        
        except Exception as e:
            logger.error(f"Error creating resolution flow: {e}")
            raise self.handle_error(e, "Failed to create resolution flow")
    
    async def auto_resolve_ticket(
        self,
        ticket_id: int,
        runbook_id: int,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Automatically resolve a ticket with high confidence
        
        Args:
            ticket_id: Ticket ID
            runbook_id: Runbook ID to execute
            confidence: Confidence score for auto-resolution
            
        Returns:
            Auto-resolution result
        """
        try:
            result = await self.orchestration_service.auto_resolve_ticket(
                db=self.db,
                ticket_id=ticket_id,
                tenant_id=self.tenant_id,
                runbook_id=runbook_id,
                confidence=confidence
            )
            return result
        
        except Exception as e:
            logger.error(f"Error auto-resolving ticket {ticket_id}: {e}")
            raise self.handle_error(e, "Failed to auto-resolve ticket")
    
    async def get_flow_status(
        self,
        flow_id: int
    ) -> Dict[str, Any]:
        """
        Get status of a resolution flow
        
        Args:
            flow_id: Flow ID
            
        Returns:
            Flow status
        """
        try:
            status = await self.orchestration_service.get_flow_status(
                db=self.db,
                flow_id=flow_id
            )
            return status
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error getting flow status: {e}")
            raise self.handle_error(e, "Failed to get flow status")
    
    async def advance_phase(
        self,
        flow_id: int,
        new_phase: str,
        phase_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Advance resolution flow to next phase
        
        Args:
            flow_id: Flow ID
            new_phase: New phase
            phase_data: Optional phase data
            
        Returns:
            Updated flow information
        """
        try:
            flow = await self.orchestration_service.advance_phase(
                db=self.db,
                flow_id=flow_id,
                new_phase=new_phase,
                phase_data=phase_data
            )
            
            return {
                "flow_id": flow.id,
                "current_phase": flow.current_phase,
                "workflow_status": flow.workflow_status,
                "message": f"Flow advanced to phase: {new_phase}"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error advancing flow phase: {e}")
            raise self.handle_error(e, "Failed to advance flow phase")
    
    async def complete_flow(
        self,
        flow_id: int,
        success: bool,
        verification_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete a resolution flow
        
        Args:
            flow_id: Flow ID
            success: Whether resolution was successful
            verification_result: Optional verification result
            
        Returns:
            Completion result
        """
        try:
            flow = await self.orchestration_service.complete_resolution_flow(
                db=self.db,
                flow_id=flow_id,
                success=success,
                verification_result=verification_result
            )
            
            return {
                "flow_id": flow.id,
                "workflow_status": flow.workflow_status,
                "current_phase": flow.current_phase,
                "completed_at": flow.completed_at.isoformat() if flow.completed_at else None,
                "message": "Resolution flow completed"
            }
        
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error completing flow: {e}")
            raise self.handle_error(e, "Failed to complete flow")








