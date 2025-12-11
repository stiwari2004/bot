"""
ResolutionFlow model for tracking end-to-end resolution workflow state
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ResolutionFlow(Base):
    """
    Tracks the complete resolution workflow state from ticket → execution → verification → closure.
    
    This model orchestrates the entire automation flow and maintains state
    across multiple iterations if needed.
    """
    
    __tablename__ = "resolution_flows"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Workflow state
    current_phase = Column(String(50), nullable=False, default='precheck')  # precheck, fix, verification, closure, escalated
    workflow_status = Column(String(50), nullable=False, default='in_progress')  # in_progress, completed, failed, escalated
    
    # Execution tracking
    execution_session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # Iteration tracking
    iteration_number = Column(Integer, nullable=False, default=1)
    max_iterations = Column(Integer, nullable=False, default=3)
    
    # Phase-specific data
    precheck_results = Column(JSONB, nullable=True)  # Precheck analysis results
    fix_results = Column(JSONB, nullable=True)  # Fix execution results
    verification_results = Column(JSONB, nullable=True)  # Verification results
    closure_data = Column(JSONB, nullable=True)  # Closure metadata
    
    # Decision tracking
    auto_resolution_enabled = Column(String(10), nullable=False, default='false')  # 'true' or 'false'
    confidence_threshold = Column(Numeric(3, 2), nullable=True)  # Confidence threshold for auto-resolution
    decision_confidence = Column(Numeric(3, 2), nullable=True)  # Actual confidence when decision was made
    
    # Alert re-checking
    alert_recheck_enabled = Column(String(10), nullable=False, default='true')  # 'true' or 'false'
    alert_recheck_results = Column(JSONB, nullable=True)  # Results of alert re-checking after fix
    
    # Metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalated_reason = Column(Text, nullable=True)
    
    # Relationships
    ticket = relationship("Ticket", backref="resolution_flows")
    execution_session = relationship("ExecutionSession", backref="resolution_flows")
    runbook = relationship("Runbook", backref="resolution_flows")
    
    __table_args__ = (
        Index("idx_resolution_flows_ticket", "ticket_id"),
        Index("idx_resolution_flows_status", "workflow_status"),
        Index("idx_resolution_flows_phase", "current_phase"),
        Index("idx_resolution_flows_started", "started_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ResolutionFlow(id={self.id}, "
            f"ticket_id={self.ticket_id}, "
            f"phase='{self.current_phase}', "
            f"status='{self.workflow_status}', "
            f"iteration={self.iteration_number})>"
        )








