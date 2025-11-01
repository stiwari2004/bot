"""
Runbook model for generated runbooks
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Runbook(Base):
    __tablename__ = "runbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body_md = Column(Text, nullable=False)  # Markdown content
    meta_data = Column(Text, nullable=True)  # JSON string with citations, etc.
    confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    parent_version_id = Column(Integer, ForeignKey("runbooks.id"), nullable=True)
    status = Column(String(20), default="draft")  # draft, approved, archived
    is_active = Column(String(10), default="active")  # active, archived, draft
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    parent_version = relationship("Runbook", remote_side=[id])
    executions = relationship("Execution", back_populates="runbook")
    
    # Indexes
    __table_args__ = (
        Index('idx_runbooks_tenant', 'tenant_id'),
        Index('idx_runbooks_title', 'title'),
        Index('idx_runbooks_confidence', 'confidence'),
        Index('idx_runbooks_parent', 'parent_version_id'),
    )
    
    def __repr__(self):
        return f"<Runbook(id={self.id}, title='{self.title}', confidence={self.confidence})>"

