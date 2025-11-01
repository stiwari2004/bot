"""
Runbook citation tracking model
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RunbookCitation(Base):
    __tablename__ = "runbook_citations"
    
    id = Column(Integer, primary_key=True, index=True)
    runbook_id = Column(Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=True)
    relevance_score = Column(Numeric(3, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        {'comment': 'Track which documents influenced runbook generation'}
    )
