"""
Execution model for runbook execution logs
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Execution(Base):
    __tablename__ = "executions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    runbook_id = Column(Integer, ForeignKey("runbooks.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    logs = Column(Text, nullable=True)
    meta_data = Column(Text, nullable=True)  # JSON string
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    runbook = relationship("Runbook", back_populates="executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_executions_tenant', 'tenant_id'),
        Index('idx_executions_runbook', 'runbook_id'),
        Index('idx_executions_status', 'status'),
        Index('idx_executions_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<Execution(id={self.id}, status='{self.status}', runbook_id={self.runbook_id})>"

