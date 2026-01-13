"""
Log Entry model for incident prediction
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class LogEntry(Base):
    """Raw log entry from various sources"""
    __tablename__ = "log_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)  # application, infrastructure, monitoring
    log_type = Column(String(50), nullable=False)  # error, warning, info, metric
    level = Column(String(20), nullable=True, index=True)  # DEBUG, INFO, WARN, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    raw_log = Column(Text, nullable=True)
    parsed_fields = Column(JSONB, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    service = Column(String(255), nullable=True, index=True)
    environment = Column(String(50), nullable=True)
    log_metadata = Column("metadata", JSONB, nullable=True)  # Renamed to avoid SQLAlchemy conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", backref="log_entries")
    
    def __repr__(self):
        return f"<LogEntry(id={self.id}, source='{self.source}', level='{self.level}', timestamp='{self.timestamp}')>"

