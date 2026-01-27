"""
ApprovalAudit model for tracking approval actions and decisions
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApprovalAudit(Base):
    """
    Tracks all approval-related actions for audit and compliance.
    
    Records approve/reject/modify decisions with reasons and outcomes,
    creating a complete audit trail for human-in-the-loop decisions.
    """
    
    __tablename__ = "approval_audits"
    
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
    
    # Action details
    action = Column(String(50), nullable=False)  # 'approve', 'reject', 'modify', 'defer'
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Decision details
    reason = Column(Text, nullable=True)  # Why this decision was made
    modified_parameters = Column(JSONB, nullable=True)  # Parameters that were modified
    original_parameters = Column(JSONB, nullable=True)  # Original parameters before modification
    
    # Outcome tracking (filled after execution completes)
    outcome = Column(String(20), nullable=True)  # 'success', 'failure', 'partial', 'pending'
    outcome_notes = Column(Text, nullable=True)  # Notes about the outcome
    
    # Additional metadata
    ip_address = Column(String(45), nullable=True)  # IP address of the user
    user_agent = Column(String(500), nullable=True)  # User agent string
    audit_metadata = Column("metadata", JSONB, nullable=True)  # Additional audit metadata (renamed to avoid SQLAlchemy conflict)
    
    # Relationships
    tenant = relationship("Tenant")
    session = relationship("ExecutionSession", backref="approval_audits")
    step = relationship("ExecutionStep", backref="approval_audits")
    user = relationship("User", foreign_keys=[user_id])
    
    __table_args__ = (
        Index("idx_approval_audits_session", "session_id"),
        Index("idx_approval_audits_step", "step_id"),
        Index("idx_approval_audits_user", "user_id"),
        Index("idx_approval_audits_action", "action"),
        Index("idx_approval_audits_timestamp", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ApprovalAudit(id={self.id}, "
            f"session_id={self.session_id}, "
            f"action='{self.action}', "
            f"timestamp={self.timestamp})>"
        )
