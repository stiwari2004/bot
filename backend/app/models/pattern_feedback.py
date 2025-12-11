"""
PatternFeedback model for storing user feedback on execution patterns and recommendations
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PatternFeedback(Base):
    """
    Stores user feedback on execution patterns and recommendations.
    
    This allows the system to learn from user feedback and improve
    pattern matching and recommendation quality over time.
    """
    
    __tablename__ = "pattern_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern_id = Column(
        Integer, ForeignKey("execution_patterns.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recommendation_id = Column(Integer, nullable=True, index=True)  # Reference to recommendation (stored in ticket meta_data)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(Integer, nullable=True, index=True)  # User who provided feedback
    
    # Feedback type: 'thumbs_up', 'thumbs_down', 'not_relevant', 'outdated', 'wrong_runbook'
    feedback_type = Column(String(50), nullable=False)
    
    # Optional reason text
    reason = Column(Text, nullable=True)
    
    # Additional metadata
    meta_data = Column(Text, nullable=True)  # JSON string for additional context
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    pattern = relationship("ExecutionPattern", backref="feedback")
    ticket = relationship("Ticket", backref="pattern_feedback")
    
    __table_args__ = (
        Index("idx_pattern_feedback_pattern", "pattern_id"),
        Index("idx_pattern_feedback_ticket", "ticket_id"),
        Index("idx_pattern_feedback_type", "feedback_type"),
        Index("idx_pattern_feedback_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<PatternFeedback(id={self.id}, "
            f"pattern_id={self.pattern_id}, "
            f"feedback_type='{self.feedback_type}', "
            f"user_id={self.user_id})>"
        )








