"""
Runbook usage tracking model
"""
from sqlalchemy import Column, Integer, Text, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RunbookUsage(Base):
    __tablename__ = "runbook_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    runbook_id = Column(Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    issue_description = Column(Text, nullable=True)
    confidence_score = Column(Numeric(3, 2), nullable=True)
    was_helpful = Column(Boolean, nullable=True)
    feedback_text = Column(Text, nullable=True)
    execution_time_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        {'comment': 'Track runbook usage, feedback, and effectiveness'}
    )
