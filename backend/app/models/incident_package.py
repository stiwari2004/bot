"""
IncidentPackage model for storing post-incident documentation
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class IncidentPackage(Base):
    """
    Stores comprehensive incident documentation for compliance and learning.
    
    Includes timeline, root cause analysis, lessons learned, and compliance data.
    """
    
    __tablename__ = "incident_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # Incident timing
    incident_start_time = Column(DateTime(timezone=True), nullable=False)
    incident_end_time = Column(DateTime(timezone=True), nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)
    
    # Analysis
    root_cause_analysis = Column(Text, nullable=True)
    timeline = Column(JSONB, nullable=True)  # Array of events with timestamps
    actions_taken = Column(JSONB, nullable=True)  # Array of steps executed
    
    # Learning
    lessons_learned = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    
    # Compliance
    compliance_data = Column(JSONB, nullable=True)  # Regulatory fields, audit trail
    
    # Generation metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    generated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    export_format = Column(String(20), nullable=True)  # 'pdf', 'markdown', 'json'
    
    # Relationships
    tenant = relationship("Tenant")
    ticket = relationship("Ticket", backref="incident_packages")
    session = relationship("ExecutionSession", backref="incident_packages")
    runbook = relationship("Runbook", backref="incident_packages")
    generator = relationship("User", foreign_keys=[generated_by])
    
    __table_args__ = (
        Index("idx_incident_packages_ticket", "ticket_id"),
        Index("idx_incident_packages_session", "session_id"),
        Index("idx_incident_packages_generated", "generated_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<IncidentPackage(id={self.id}, "
            f"ticket_id={self.ticket_id}, "
            f"generated_at={self.generated_at})>"
        )
