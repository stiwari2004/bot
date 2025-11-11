"""
Resolution Verification Service - Verify if ticket issue is actually resolved
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.ticket_status_service import get_ticket_status_service
from typing import Optional, Dict, Any
from datetime import datetime

logger = get_logger(__name__)


class ResolutionVerificationService:
    """Service for verifying if ticket issues are resolved after runbook execution"""
    
    def __init__(self):
        self.ticket_status_service = get_ticket_status_service()
    
    async def verify_resolution(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify if the ticket issue is resolved after execution
        
        Args:
            db: Database session
            session_id: Execution session ID
            ticket_id: Ticket ID (optional, will fetch from session if not provided)
            
        Returns:
            {
                "resolved": bool,
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "verification_method": str
            }
        """
        try:
            # Get execution session
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise ValueError(f"Execution session {session_id} not found")
            
            # Get ticket ID from session if not provided
            if not ticket_id:
                ticket_id = session.ticket_id
            
            if not ticket_id:
                logger.warning(f"No ticket_id for session {session_id}, skipping resolution verification")
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "No ticket associated with execution",
                    "verification_method": "none"
                }
            
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found")
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "Ticket not found",
                    "verification_method": "none"
                }
            
            # Check execution status
            if session.status != "completed":
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": f"Execution not completed (status: {session.status})",
                    "verification_method": "execution_status"
                }
            
            # Method 1: Check if all steps succeeded
            all_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id
            ).all()
            
            if not all_steps:
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "No execution steps found",
                    "verification_method": "step_analysis"
                }
            
            # Check step success rate
            successful_steps = [s for s in all_steps if s.completed and s.success]
            failed_steps = [s for s in all_steps if s.completed and s.success is False]
            
            success_rate = len(successful_steps) / len(all_steps) if all_steps else 0.0
            
            # Method 2: Check postchecks (if they exist)
            postchecks = [s for s in all_steps if s.step_type == "postcheck"]
            postcheck_success = all(s.success for s in postchecks if s.completed)
            
            # High confidence if all steps succeeded and postchecks passed
            if success_rate == 1.0 and (not postchecks or postcheck_success):
                resolved = True
                confidence = 0.9
                reasoning = "All execution steps completed successfully"
                verification_method = "step_analysis"
            
            # Medium confidence if most steps succeeded
            elif success_rate >= 0.8:
                resolved = True
                confidence = 0.7
                reasoning = f"Most steps succeeded ({len(successful_steps)}/{len(all_steps)})"
                verification_method = "step_analysis"
            
            # Low confidence if mixed results
            elif success_rate >= 0.5:
                resolved = False  # Uncertain, need manual verification
                confidence = 0.5
                reasoning = f"Mixed results ({len(successful_steps)}/{len(all_steps)} steps succeeded)"
                verification_method = "step_analysis"
            
            # Low confidence if most steps failed
            else:
                resolved = False
                confidence = 0.9
                reasoning = f"Most steps failed ({len(failed_steps)}/{len(all_steps)} steps failed)"
                verification_method = "step_analysis"
            
            # Update ticket status based on verification
            if resolved:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, ticket_id, "completed", issue_resolved=True
                )
            else:
                # Keep as in_progress for manual review if uncertain
                if confidence < 0.7:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, ticket_id, "completed", issue_resolved=None
                    )
                else:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, ticket_id, "completed", issue_resolved=False
                    )
            
            logger.info(
                f"Resolution verification for ticket {ticket_id}: "
                f"resolved={resolved}, confidence={confidence:.2f}, method={verification_method}"
            )
            
            return {
                "resolved": resolved,
                "confidence": confidence,
                "reasoning": reasoning,
                "verification_method": verification_method,
                "success_rate": success_rate,
                "total_steps": len(all_steps),
                "successful_steps": len(successful_steps),
                "failed_steps": len(failed_steps)
            }
            
        except Exception as e:
            logger.error(f"Error verifying resolution for session {session_id}: {e}")
            return {
                "resolved": False,
                "confidence": 0.0,
                "reasoning": f"Verification failed: {str(e)}",
                "verification_method": "error"
            }
    
    async def verify_resolution_with_llm(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify resolution using LLM analysis of execution output
        This is a more sophisticated method that analyzes step outputs
        """
        # For POC, we'll use the step-based verification
        # In production, this could analyze step outputs with LLM
        result = await self.verify_resolution(db, session_id, ticket_id)
        
        # TODO: Enhance with LLM analysis of step outputs
        # This would involve:
        # 1. Collecting all step outputs
        # 2. Analyzing them with LLM to determine if issue is resolved
        # 3. Returning higher confidence result
        
        return result


# Global instance
_resolution_verification_service: Optional[ResolutionVerificationService] = None


def get_resolution_verification_service() -> ResolutionVerificationService:
    """Get or create resolution verification service instance"""
    global _resolution_verification_service
    if _resolution_verification_service is None:
        _resolution_verification_service = ResolutionVerificationService()
    return _resolution_verification_service




