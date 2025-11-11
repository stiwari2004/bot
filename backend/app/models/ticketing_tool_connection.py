"""
Ticketing Tool Connection Model
Stores configuration for connecting to external ticketing tools
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class TicketingToolConnection(Base):
    __tablename__ = "ticketing_tool_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)  # servicenow, zendesk, jira, etc.
    connection_type = Column(String(20), nullable=False)  # webhook, api_poll, api_push
    is_active = Column(Boolean, default=True)
    
    # Webhook configuration
    webhook_url = Column(Text, nullable=True)  # Our webhook URL to give to the tool
    webhook_secret = Column(Text, nullable=True)  # Secret for webhook verification
    
    # API configuration (for polling or push)
    api_base_url = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)  # Encrypted
    api_username = Column(String(255), nullable=True)
    api_password = Column(Text, nullable=True)  # Encrypted
    
    # Connection metadata
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(20), nullable=True)  # success, failed, pending
    last_error = Column(Text, nullable=True)
    sync_interval_minutes = Column(Integer, default=5)  # For polling
    
    # Additional configuration
    meta_data = Column(Text, nullable=True)  # JSON string with tool-specific config
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticketing_tool_tenant', 'tenant_id'),
        Index('idx_ticketing_tool_name', 'tool_name'),
        Index('idx_ticketing_tool_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TicketingToolConnection(id={self.id}, tool='{self.tool_name}', active={self.is_active})>"



