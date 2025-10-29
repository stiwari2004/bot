"""
Audit model for tracking changes
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Audit(Base):
    __tablename__ = "audits"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    actor = Column(String(255), nullable=False)  # user email or system
    action = Column(String(100), nullable=False)  # create, update, delete, execute
    entity = Column(String(100), nullable=False)  # document, runbook, execution
    entity_id = Column(Integer, nullable=False)
    diff = Column(Text, nullable=True)  # JSON string with changes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_audits_tenant', 'tenant_id'),
        Index('idx_audits_actor', 'actor'),
        Index('idx_audits_entity', 'entity', 'entity_id'),
        Index('idx_audits_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Audit(id={self.id}, action='{self.action}', entity='{self.entity}')>"

