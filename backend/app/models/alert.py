"""
Alert model for storing alerts from monitoring tools
Alerts are separate from tickets - tickets come from ticketing tools
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # ID from monitoring tool (fingerprint, alert_id, etc.)
    source = Column(String(100), nullable=False)  # prometheus, datadog, azure_monitor, splunk
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    environment = Column(String(20), nullable=False)  # prod, staging, dev
    service = Column(String(255), nullable=True)  # Service/component name
    status = Column(String(50), default="firing")  # firing, resolved, acknowledged
    raw_payload = Column(JSON, nullable=True)  # Original payload from monitoring tool
    meta_data = Column(JSON, nullable=True)  # Additional metadata (labels, annotations, etc.)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)  # When alert started
    ends_at = Column(DateTime(timezone=True), nullable=True)  # When alert ended/resolved
    
    # Link to ticket if matched
    matched_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    matched_at = Column(DateTime(timezone=True), nullable=True)  # When matched with ticket
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    matched_ticket = relationship("Ticket", foreign_keys=[matched_ticket_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_alerts_tenant', 'tenant_id'),
        Index('idx_alerts_source', 'source'),
        Index('idx_alerts_status', 'status'),
        Index('idx_alerts_external_id', 'external_id'),
        Index('idx_alerts_matched_ticket', 'matched_ticket_id'),
    )
    
    def __repr__(self):
        return f"<Alert(id={self.id}, source='{self.source}', title='{self.title[:50]}...', status='{self.status}')>"


