"""
Metadata mapping model for storing learned input extraction mappings
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class MetadataMapping(Base):
    """Store learned metadata mappings for automatic input extraction"""
    
    __tablename__ = "metadata_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    input_name = Column(String(100), nullable=False)  # e.g., "host_ip"
    source = Column(String(50), nullable=False)  # "datadog", "servicenow"
    metadata_path = Column(String(255), nullable=False)  # e.g., "tags.host", "configuration_item.ip_address"
    confidence = Column(Float, default=0.8)  # Confidence score (0.0-1.0)
    usage_count = Column(Integer, default=1)  # How many times used
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)  # Can be deactivated if mapping is wrong
    
    # Indexes
    __table_args__ = (
        Index('idx_mapping_source_input', 'source', 'input_name'),
        Index('idx_mapping_tenant', 'tenant_id'),
        Index('idx_mapping_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<MetadataMapping(id={self.id}, input='{self.input_name}', path='{self.metadata_path}', confidence={self.confidence})>"




