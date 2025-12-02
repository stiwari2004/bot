"""
ConfidenceBreakdownRepository
Data access layer for ConfidenceBreakdown model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.confidence_breakdown import ConfidenceBreakdown


class ConfidenceBreakdownRepository(BaseRepository[ConfidenceBreakdown]):
    """Repository for ConfidenceBreakdown operations"""
    
    def __init__(self, db: Session):
        super().__init__(ConfidenceBreakdown, db)
    
    def get_by_runbook(
        self, 
        runbook_id: int, 
        tenant_id: Optional[int] = None
    ) -> Optional[ConfidenceBreakdown]:
        """Get most recent confidence breakdown for a runbook"""
        query = self.db.query(ConfidenceBreakdown).filter(
            ConfidenceBreakdown.runbook_id == runbook_id
        )
        if tenant_id:
            query = query.filter(ConfidenceBreakdown.tenant_id == tenant_id)
        return query.order_by(ConfidenceBreakdown.created_at.desc()).first()
    
    def get_by_ticket(
        self,
        ticket_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[ConfidenceBreakdown]:
        """Get confidence breakdown for a ticket/recommendation"""
        query = self.db.query(ConfidenceBreakdown).filter(
            ConfidenceBreakdown.ticket_id == ticket_id
        )
        if tenant_id:
            query = query.filter(ConfidenceBreakdown.tenant_id == tenant_id)
        return query.order_by(ConfidenceBreakdown.created_at.desc()).first()
    
    def get_by_recommendation(
        self,
        recommendation_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[ConfidenceBreakdown]:
        """Get confidence breakdown for a recommendation"""
        query = self.db.query(ConfidenceBreakdown).filter(
            ConfidenceBreakdown.recommendation_id == recommendation_id
        )
        if tenant_id:
            query = query.filter(ConfidenceBreakdown.tenant_id == tenant_id)
        return query.order_by(ConfidenceBreakdown.created_at.desc()).first()
    
    def get_recent_breakdowns(
        self,
        tenant_id: int,
        limit: int = 50
    ) -> List[ConfidenceBreakdown]:
        """Get recent confidence breakdowns for a tenant"""
        return self.db.query(ConfidenceBreakdown).filter(
            ConfidenceBreakdown.tenant_id == tenant_id
        ).order_by(ConfidenceBreakdown.created_at.desc()).limit(limit).all()

