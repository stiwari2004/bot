"""
Log Pattern model for incident prediction
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class LogPattern(Base):
    """Extracted pattern from logs"""
    __tablename__ = "log_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern_signature = Column(String(500), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=True, index=True)  # error_pattern, warning_pattern, anomaly
    frequency = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    associated_incidents = Column(Integer, default=0)
    confidence_score = Column(Float, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", backref="log_patterns")
    predictions = relationship("PredictionPattern", back_populates="pattern")
    
    def __repr__(self):
        return f"<LogPattern(id={self.id}, pattern_signature='{self.pattern_signature[:50]}...', type='{self.pattern_type}')>"

