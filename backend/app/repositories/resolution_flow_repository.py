"""
ResolutionFlowRepository
Data access layer for ResolutionFlow model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.resolution_flow import ResolutionFlow


class ResolutionFlowRepository(BaseRepository[ResolutionFlow]):
    """Repository for ResolutionFlow operations"""
    
    def __init__(self, db: Session):
        super().__init__(ResolutionFlow, db)
    
    def get_by_ticket(
        self,
        ticket_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[ResolutionFlow]:
        """Get resolution flow for a ticket"""
        query = self.db.query(ResolutionFlow).filter(
            ResolutionFlow.ticket_id == ticket_id
        )
        if tenant_id:
            query = query.filter(ResolutionFlow.tenant_id == tenant_id)
        return query.order_by(ResolutionFlow.started_at.desc()).first()
    
    def get_by_status(
        self,
        tenant_id: int,
        workflow_status: str,
        limit: int = 100
    ) -> List[ResolutionFlow]:
        """Get flows by workflow status"""
        return self.db.query(ResolutionFlow).filter(
            ResolutionFlow.tenant_id == tenant_id,
            ResolutionFlow.workflow_status == workflow_status
        ).order_by(ResolutionFlow.started_at.desc()).limit(limit).all()
    
    def get_by_phase(
        self,
        tenant_id: int,
        current_phase: str,
        limit: int = 100
    ) -> List[ResolutionFlow]:
        """Get flows by current phase"""
        return self.db.query(ResolutionFlow).filter(
            ResolutionFlow.tenant_id == tenant_id,
            ResolutionFlow.current_phase == current_phase
        ).order_by(ResolutionFlow.started_at.desc()).limit(limit).all()
    
    def get_active_flows(
        self,
        tenant_id: int,
        limit: int = 100
    ) -> List[ResolutionFlow]:
        """Get all active (in_progress) flows"""
        return self.db.query(ResolutionFlow).filter(
            ResolutionFlow.tenant_id == tenant_id,
            ResolutionFlow.workflow_status == 'in_progress'
        ).order_by(ResolutionFlow.started_at.desc()).limit(limit).all()








