"""
ParameterTuning model for tracking parameter modifications during execution
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ParameterTuning(Base):
    """
    Tracks parameter tuning/modifications made during execution approval.
    
    This allows operators to adjust runbook parameters without code changes
    and tracks the effectiveness of these modifications.
    """
    
    __tablename__ = "parameter_tunings"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id = Column(
        Integer, ForeignKey("execution_steps.id", ondelete="CASCADE"), nullable=True, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    # Parameter details
    parameter_name = Column(String(255), nullable=False)  # e.g., "timeout", "retry_count"
    parameter_type = Column(String(50), nullable=True)  # e.g., "string", "number", "boolean"
    original_value = Column(Text, nullable=True)  # Original parameter value (JSON string)
    tuned_value = Column(Text, nullable=False)  # Modified parameter value (JSON string)
    
    # Tuning metadata
    tuned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tuned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(Text, nullable=True)  # Why the parameter was tuned
    
    # Effectiveness tracking (filled after execution)
    effectiveness_score = Column(Numeric(5, 2), nullable=True)  # 0-100 score
    execution_success = Column(String(10), nullable=True)  # 'success', 'failure', 'partial'
    notes = Column(Text, nullable=True)  # Post-execution notes
    
    # Relationships
    tenant = relationship("Tenant")
    session = relationship("ExecutionSession", backref="parameter_tunings")
    step = relationship("ExecutionStep", backref="parameter_tunings")
    runbook = relationship("Runbook", backref="parameter_tunings")
    tuner = relationship("User", foreign_keys=[tuned_by])
    
    __table_args__ = (
        Index("idx_parameter_tunings_session", "session_id"),
        Index("idx_parameter_tunings_step", "step_id"),
        Index("idx_parameter_tunings_runbook", "runbook_id"),
        Index("idx_parameter_tunings_tuned_at", "tuned_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ParameterTuning(id={self.id}, "
            f"session_id={self.session_id}, "
            f"parameter_name='{self.parameter_name}')>"
        )
