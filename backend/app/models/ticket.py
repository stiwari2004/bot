"""
Ticket model for storing tickets from monitoring tools
POC version - simplified schema
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # ID from monitoring tool
    source = Column(String(100), nullable=False)  # prometheus, datadog, pagerduty, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    environment = Column(String(20), nullable=False)  # prod, staging, dev
    service = Column(String(255), nullable=True)  # Service/component name
    status = Column(String(50), default="open")  # open, analyzing, in_progress, resolved, closed, escalated
    classification = Column(String(50), nullable=True)  # false_positive, true_positive, uncertain
    classification_confidence = Column(String(10), nullable=True)  # high, medium, low
    raw_payload = Column(JSON, nullable=True)  # Original payload from monitoring tool
    meta_data = Column(JSON, nullable=True)  # Additional metadata (renamed from metadata to avoid SQLAlchemy conflict)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    execution_sessions = relationship("ExecutionSession", back_populates="ticket")
    
    # Indexes
    __table_args__ = (
        Index('idx_tickets_tenant', 'tenant_id'),
        Index('idx_tickets_source', 'source'),
        Index('idx_tickets_status', 'status'),
        Index('idx_tickets_external_id', 'external_id'),
        Index('idx_tickets_classification', 'classification'),
    )
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, source='{self.source}', title='{self.title[:50]}...')>"

