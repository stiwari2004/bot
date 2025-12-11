"""
Monitoring Tool Connection Model
Stores configuration for connecting to external monitoring tools
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class MonitoringToolConnection(Base):
    __tablename__ = "monitoring_tool_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)  # prometheus, datadog, azure_monitor, splunk
    connection_type = Column(String(20), nullable=False)  # webhook, api
    is_active = Column(Boolean, default=True)
    
    # Webhook configuration (for receiving alerts)
    webhook_url = Column(Text, nullable=True)  # Our webhook URL to give to the tool
    
    # API configuration (for updating alerts back to the tool)
    api_base_url = Column(Text, nullable=True)  # e.g., https://api.datadoghq.com, http://prometheus:9093
    api_key = Column(Text, nullable=True)  # Encrypted API key
    api_username = Column(String(255), nullable=True)
    api_password = Column(Text, nullable=True)  # Encrypted password
    application_key = Column(Text, nullable=True)  # For Datadog (encrypted)
    
    # Connection metadata
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(20), nullable=True)  # success, failed, pending
    last_error = Column(Text, nullable=True)
    
    # Additional configuration
    meta_data = Column(Text, nullable=True)  # JSON string with tool-specific config
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    
    # Indexes
    __table_args__ = (
        Index('idx_monitoring_tool_tenant', 'tenant_id'),
        Index('idx_monitoring_tool_name', 'tool_name'),
        Index('idx_monitoring_tool_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<MonitoringToolConnection(id={self.id}, tool='{self.tool_name}', active={self.is_active})>"









