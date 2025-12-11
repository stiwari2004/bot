"""
ConfidenceBreakdown model for storing detailed confidence score components
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConfidenceBreakdown(Base):
    """
    Stores detailed confidence score breakdown for runbooks and recommendations.
    
    This allows transparency into how confidence scores are calculated
    and helps identify areas for improvement.
    """
    
    __tablename__ = "confidence_breakdowns"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # References (one of these will be set)
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recommendation_id = Column(Integer, nullable=True, index=True)  # Reference to recommendation (stored in ticket meta_data)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    # Overall confidence score (0-100)
    overall_confidence = Column(Numeric(5, 2), nullable=False)
    
    # Component scores (0-100 each)
    search_quality_score = Column(Numeric(5, 2), nullable=False)  # Factor 1: 40% weight
    llm_consistency_score = Column(Numeric(5, 2), nullable=True)  # Factor 2: 30% weight
    yaml_quality_score = Column(Numeric(5, 2), nullable=True)  # Factor 3: 20% weight
    citation_coverage_score = Column(Numeric(5, 2), nullable=True)  # Factor 4: 10% weight
    
    # Detailed metadata
    search_quality_details = Column(JSONB, nullable=True)  # Top score, result count, avg relevance
    llm_consistency_details = Column(JSONB, nullable=True)  # Consistency checks, warnings
    yaml_quality_details = Column(JSONB, nullable=True)  # Structure validation, completeness
    citation_coverage_details = Column(JSONB, nullable=True)  # Citation count, avg relevance, diversity
    
    # Warnings and flags
    warnings = Column(JSONB, nullable=True)  # Array of warning messages
    flags = Column(JSONB, nullable=True)  # Array of flag types (low_confidence, hallucination, etc.)
    
    # Metadata
    calculation_method = Column(Text, nullable=True)  # Method used for calculation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    runbook = relationship("Runbook", backref="confidence_breakdowns")
    ticket = relationship("Ticket", backref="confidence_breakdowns")
    
    __table_args__ = (
        Index("idx_confidence_breakdown_runbook", "runbook_id"),
        Index("idx_confidence_breakdown_ticket", "ticket_id"),
        Index("idx_confidence_breakdown_confidence", "overall_confidence"),
        Index("idx_confidence_breakdown_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ConfidenceBreakdown(id={self.id}, "
            f"runbook_id={self.runbook_id}, "
            f"overall_confidence={self.overall_confidence})>"
        )








