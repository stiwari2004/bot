"""
Runbook similarity tracking model
"""
from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RunbookSimilarity(Base):
    __tablename__ = "runbook_similarities"
    
    id = Column(Integer, primary_key=True, index=True)
    runbook_id_1 = Column(Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    runbook_id_2 = Column(Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Numeric(3, 2), nullable=False)
    status = Column(String(20), default='detected', index=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {'comment': 'Track duplicate runbook detection and resolution'}
    )
