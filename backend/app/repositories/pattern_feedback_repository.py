"""
PatternFeedbackRepository
Data access layer for PatternFeedback model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.pattern_feedback import PatternFeedback


class PatternFeedbackRepository(BaseRepository[PatternFeedback]):
    """Repository for PatternFeedback operations"""
    
    def __init__(self, db: Session):
        super().__init__(PatternFeedback, db)
    
    def get_by_pattern(self, pattern_id: int, tenant_id: Optional[int] = None) -> List[PatternFeedback]:
        """Get all feedback for a specific pattern"""
        query = self.db.query(PatternFeedback).filter(
            PatternFeedback.pattern_id == pattern_id
        )
        if tenant_id:
            query = query.filter(PatternFeedback.tenant_id == tenant_id)
        return query.order_by(PatternFeedback.created_at.desc()).all()
    
    def get_by_ticket(self, ticket_id: int, tenant_id: Optional[int] = None) -> List[PatternFeedback]:
        """Get all feedback for a specific ticket"""
        query = self.db.query(PatternFeedback).filter(
            PatternFeedback.ticket_id == ticket_id
        )
        if tenant_id:
            query = query.filter(PatternFeedback.tenant_id == tenant_id)
        return query.order_by(PatternFeedback.created_at.desc()).all()
    
    def get_by_feedback_type(
        self, 
        feedback_type: str, 
        tenant_id: Optional[int] = None,
        limit: int = 100
    ) -> List[PatternFeedback]:
        """Get feedback by type (e.g., 'thumbs_down')"""
        query = self.db.query(PatternFeedback).filter(
            PatternFeedback.feedback_type == feedback_type
        )
        if tenant_id:
            query = query.filter(PatternFeedback.tenant_id == tenant_id)
        return query.order_by(PatternFeedback.created_at.desc()).limit(limit).all()
    
    def get_recent_feedback(
        self, 
        tenant_id: int, 
        limit: int = 50
    ) -> List[PatternFeedback]:
        """Get recent feedback for a tenant"""
        return self.db.query(PatternFeedback).filter(
            PatternFeedback.tenant_id == tenant_id
        ).order_by(PatternFeedback.created_at.desc()).limit(limit).all()








