"""
CitationVerification model for tracking citation verification status
"""
from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CitationVerification(Base):
    """
    Tracks verification status and quality scores for runbook citations.
    
    This allows monitoring of citation health and identifying broken
    or outdated citations.
    """
    
    __tablename__ = "citation_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    citation_id = Column(
        Integer, ForeignKey("runbook_citations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Verification status
    verification_status = Column(String(50), nullable=False, default='pending')  # 'verified', 'broken', 'pending', 'outdated'
    
    # Quality scores (0-100)
    relevance_score = Column(Numeric(5, 2), nullable=True)  # Citation relevance
    recency_score = Column(Numeric(5, 2), nullable=True)  # Document recency
    source_type_score = Column(Numeric(5, 2), nullable=True)  # Source type quality
    overall_quality_score = Column(Numeric(5, 2), nullable=True)  # Overall quality
    
    # Verification details
    document_exists = Column(String(10), nullable=True)  # 'true', 'false', 'unknown'
    document_accessible = Column(String(10), nullable=True)  # 'true', 'false', 'unknown'
    chunk_valid = Column(String(10), nullable=True)  # 'true', 'false', 'unknown'
    
    # Metadata
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)  # Additional notes about verification
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    citation = relationship("RunbookCitation", backref="verifications")
    runbook = relationship("Runbook", backref="citation_verifications")
    
    __table_args__ = (
        Index("idx_citation_verifications_citation", "citation_id"),
        Index("idx_citation_verifications_runbook", "runbook_id"),
        Index("idx_citation_verifications_status", "verification_status"),
        Index("idx_citation_verifications_quality", "overall_quality_score"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<CitationVerification(id={self.id}, "
            f"citation_id={self.citation_id}, "
            f"status='{self.verification_status}', "
            f"quality={self.overall_quality_score})>"
        )

