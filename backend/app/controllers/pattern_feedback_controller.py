"""
PatternFeedbackController
Handles HTTP requests for pattern feedback operations
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.pattern_feedback_repository import PatternFeedbackRepository
from app.services.decision.pattern_feedback_service import PatternFeedbackService
from app.models.pattern_feedback import PatternFeedback
from app.core.logging import get_logger

logger = get_logger(__name__)


class PatternFeedbackController(BaseController):
    """Controller for pattern feedback operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.feedback_repo = PatternFeedbackRepository(db)
        self.feedback_service = PatternFeedbackService()
    
    async def submit_feedback(
        self,
        pattern_id: Optional[int] = None,
        recommendation_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        feedback_type: str = "thumbs_down",
        reason: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit feedback on a pattern or recommendation
        
        Args:
            pattern_id: Pattern ID (optional)
            recommendation_id: Recommendation ID (optional)
            ticket_id: Ticket ID (optional)
            user_id: User ID (optional)
            feedback_type: Type of feedback
            reason: Optional reason text
            meta_data: Optional metadata
            
        Returns:
            Feedback submission result
        """
        try:
            # Validate feedback type
            valid_types = ['thumbs_up', 'thumbs_down', 'not_relevant', 'outdated', 'wrong_runbook']
            if feedback_type not in valid_types:
                raise self.bad_request(f"Invalid feedback_type. Must be one of: {', '.join(valid_types)}")
            
            # Submit feedback
            feedback = await self.feedback_service.submit_feedback(
                db=self.db,
                tenant_id=self.tenant_id,
                pattern_id=pattern_id,
                recommendation_id=recommendation_id,
                ticket_id=ticket_id,
                user_id=user_id,
                feedback_type=feedback_type,
                reason=reason,
                meta_data=meta_data,
            )
            
            return {
                "feedback_id": feedback.id,
                "message": "Feedback submitted successfully",
                "pattern_id": feedback.pattern_id,
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            raise self.handle_error(e, "Failed to submit feedback")
    
    async def get_feedback_summary(
        self,
        pattern_id: int
    ) -> Dict[str, Any]:
        """
        Get feedback summary for a pattern
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Feedback summary dictionary
        """
        try:
            summary = await self.feedback_service.get_feedback_summary(
                db=self.db,
                pattern_id=pattern_id,
                tenant_id=self.tenant_id
            )
            
            return summary
        
        except Exception as e:
            logger.error(f"Error getting feedback summary: {e}")
            raise self.handle_error(e, "Failed to get feedback summary")
    
    async def get_ticket_feedback(
        self,
        ticket_id: int
    ) -> Dict[str, Any]:
        """
        Get all feedback for a ticket
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            List of feedback items
        """
        try:
            feedback_list = self.feedback_repo.get_by_ticket(ticket_id, self.tenant_id)
            
            return {
                "ticket_id": ticket_id,
                "feedback_count": len(feedback_list),
                "feedback": [
                    {
                        "id": f.id,
                        "pattern_id": f.pattern_id,
                        "feedback_type": f.feedback_type,
                        "reason": f.reason,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in feedback_list
                ]
            }
        
        except Exception as e:
            logger.error(f"Error getting ticket feedback: {e}")
            raise self.handle_error(e, "Failed to get ticket feedback")

