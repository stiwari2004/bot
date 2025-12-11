"""
PatternFeedbackService
Processes user feedback on patterns and recommendations, updating pattern scores accordingly
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.pattern_feedback import PatternFeedback
from app.models.execution_pattern import ExecutionPattern
from app.repositories.pattern_feedback_repository import PatternFeedbackRepository
from app.services.decision.pattern_storage_service import PatternStorageService

logger = get_logger(__name__)


class PatternFeedbackService:
    """Service for processing pattern feedback and updating pattern scores"""
    
    def __init__(self):
        self.pattern_storage_service = PatternStorageService()
    
    async def submit_feedback(
        self,
        db: Session,
        *,
        tenant_id: int,
        pattern_id: Optional[int] = None,
        recommendation_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        user_id: Optional[int] = None,
        feedback_type: str,
        reason: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ) -> PatternFeedback:
        """
        Submit feedback on a pattern or recommendation
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            pattern_id: Pattern ID (optional)
            recommendation_id: Recommendation ID (optional, stored in ticket meta_data)
            ticket_id: Ticket ID (optional)
            user_id: User ID who provided feedback
            feedback_type: Type of feedback ('thumbs_up', 'thumbs_down', 'not_relevant', 'outdated', 'wrong_runbook')
            reason: Optional reason text
            meta_data: Optional additional metadata
            
        Returns:
            Created PatternFeedback object
        """
        import json
        
        # Create feedback record
        feedback = PatternFeedback(
            tenant_id=tenant_id,
            pattern_id=pattern_id,
            recommendation_id=recommendation_id,
            ticket_id=ticket_id,
            user_id=user_id,
            feedback_type=feedback_type,
            reason=reason,
            meta_data=json.dumps(meta_data) if meta_data else None,
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(
            f"Feedback submitted: id={feedback.id}, pattern_id={pattern_id}, "
            f"type={feedback_type}, user_id={user_id}"
        )
        
        # Update pattern success rate if pattern_id is provided
        if pattern_id:
            await self._update_pattern_from_feedback(db, pattern_id, feedback_type)
        
        return feedback
    
    async def _update_pattern_from_feedback(
        self,
        db: Session,
        pattern_id: int,
        feedback_type: str
    ) -> None:
        """
        Update pattern success rate based on feedback
        
        Negative feedback reduces success rate, positive feedback increases it
        """
        pattern = db.query(ExecutionPattern).filter(
            ExecutionPattern.id == pattern_id
        ).first()
        
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found for feedback update")
            return
        
        # Determine if feedback is positive or negative
        is_positive = feedback_type in ['thumbs_up']
        is_negative = feedback_type in ['thumbs_down', 'wrong_runbook', 'outdated', 'not_relevant']
        
        if not (is_positive or is_negative):
            logger.warning(f"Unknown feedback type: {feedback_type}")
            return
        
        # Adjust success rate
        # For positive feedback: increase by 2%
        # For negative feedback: decrease by 5%
        current_rate = float(pattern.success_rate or 0.0)
        
        if is_positive:
            new_rate = min(100.0, current_rate + 2.0)
        else:  # is_negative
            new_rate = max(0.0, current_rate - 5.0)
        
        pattern.success_rate = new_rate
        db.add(pattern)
        db.commit()
        
        logger.info(
            f"Updated pattern {pattern_id} success rate: {current_rate:.2f}% -> {new_rate:.2f}% "
            f"(feedback: {feedback_type})"
        )
    
    async def get_feedback_summary(
        self,
        db: Session,
        pattern_id: int,
        tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get summary of feedback for a pattern
        
        Returns:
            Dictionary with feedback counts and breakdown
        """
        repo = PatternFeedbackRepository(db)
        all_feedback = repo.get_by_pattern(pattern_id, tenant_id)
        
        summary = {
            "total_feedback": len(all_feedback),
            "thumbs_up": sum(1 for f in all_feedback if f.feedback_type == "thumbs_up"),
            "thumbs_down": sum(1 for f in all_feedback if f.feedback_type == "thumbs_down"),
            "not_relevant": sum(1 for f in all_feedback if f.feedback_type == "not_relevant"),
            "outdated": sum(1 for f in all_feedback if f.feedback_type == "outdated"),
            "wrong_runbook": sum(1 for f in all_feedback if f.feedback_type == "wrong_runbook"),
            "recent_feedback": [
                {
                    "id": f.id,
                    "feedback_type": f.feedback_type,
                    "reason": f.reason,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in all_feedback[:5]  # Last 5 feedback items
            ]
        }
        
        return summary








