"""
Change Ticket model for tracking change windows
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class ChangeTicket(Base):
    __tablename__ = "change_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=False)  # Change ticket ID from ticketing tool
    source = Column(String(100), nullable=False)  # servicenow, manageengine, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    change_type = Column(String(50), nullable=True)  # standard, emergency, normal
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    affected_services = Column(ARRAY(String(255)), nullable=True)  # Array of service names (PostgreSQL)
    affected_environments = Column(ARRAY(String(255)), nullable=True)  # Array of environments (PostgreSQL)
    suppression_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="change_tickets")
    
    # Indexes
    __table_args__ = (
        Index('idx_change_tickets_tenant', 'tenant_id'),
        Index('idx_change_tickets_time', 'start_time', 'end_time'),
        Index('idx_change_tickets_status', 'status'),
        Index('idx_change_tickets_external', 'tenant_id', 'external_id', 'source'),
    )
    
    def is_active(self) -> bool:
        """Check if change window is currently active"""
        now = datetime.now(timezone.utc)
        return (
            self.status in ('scheduled', 'in_progress') and
            self.start_time <= now <= self.end_time and
            self.suppression_enabled
        )
    
    def affects_service(self, service_name: str) -> bool:
        """Check if change affects a specific service"""
        if not self.affected_services:
            return True  # If no services specified, affects all
        return service_name.lower() in [s.lower() for s in self.affected_services]
    
    def affects_environment(self, environment: str) -> bool:
        """Check if change affects a specific environment"""
        if not self.affected_environments:
            return True  # If no environments specified, affects all
        return environment.lower() in [e.lower() for e in self.affected_environments]
    
    def __repr__(self):
        return f"<ChangeTicket(id={self.id}, external_id='{self.external_id}', status='{self.status}')>"

