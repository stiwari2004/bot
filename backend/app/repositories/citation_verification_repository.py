"""
CitationVerificationRepository
Data access layer for CitationVerification model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.citation_verification import CitationVerification


class CitationVerificationRepository(BaseRepository[CitationVerification]):
    """Repository for CitationVerification operations"""
    
    def __init__(self, db: Session):
        super().__init__(CitationVerification, db)
    
    def get_by_runbook(
        self,
        runbook_id: int,
        tenant_id: Optional[int] = None
    ) -> List[CitationVerification]:
        """Get all citation verifications for a runbook"""
        query = self.db.query(CitationVerification).filter(
            CitationVerification.runbook_id == runbook_id
        )
        if tenant_id:
            query = query.filter(CitationVerification.tenant_id == tenant_id)
        return query.order_by(CitationVerification.created_at.desc()).all()
    
    def get_by_citation(
        self,
        citation_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[CitationVerification]:
        """Get verification for a specific citation"""
        query = self.db.query(CitationVerification).filter(
            CitationVerification.citation_id == citation_id
        )
        if tenant_id:
            query = query.filter(CitationVerification.tenant_id == tenant_id)
        return query.order_by(CitationVerification.created_at.desc()).first()
    
    def get_by_status(
        self,
        runbook_id: int,
        status: str,
        tenant_id: Optional[int] = None
    ) -> List[CitationVerification]:
        """Get verifications by status (e.g., 'broken', 'verified')"""
        query = self.db.query(CitationVerification).filter(
            CitationVerification.runbook_id == runbook_id,
            CitationVerification.verification_status == status
        )
        if tenant_id:
            query = query.filter(CitationVerification.tenant_id == tenant_id)
        return query.all()
    
    def get_broken_citations(
        self,
        runbook_id: int,
        tenant_id: Optional[int] = None
    ) -> List[CitationVerification]:
        """Get all broken citations for a runbook"""
        return self.get_by_status(runbook_id, 'broken', tenant_id)








