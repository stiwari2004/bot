"""
RunbookQuarantine model for tracking quarantined runbooks
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class RunbookQuarantine(Base):
    """
    Tracks runbook quarantine status to prevent automation storms.
    
    Quarantines can be:
    - Auto-quarantine: After N consecutive failures
    - Manual: Admin-initiated quarantine
    - Review flag: Flagged for review before re-enable
    
    Quarantines are version-aware - specific runbook versions can be quarantined
    without affecting other versions.
    """
    
    __tablename__ = "runbook_quarantines"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_version_id = Column(
        Integer, ForeignKey("runbook_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # Quarantine details
    quarantine_reason = Column(String(50), nullable=False)  # 'auto_quarantine', 'manual', 'review_flag'
    failure_count = Column(Integer, nullable=False, default=0)  # Consecutive failures
    
    # Failure pattern tracking
    failure_pattern = Column(JSONB, nullable=True)  # Array of failure details:
    # {
    #   "errors": [{"error": "...", "timestamp": "...", "step_number": 1}],
    #   "error_types": ["timeout", "connection_error"],
    #   "same_error": true/false,
    #   "varied_errors": true/false
    # }
    
    # Quarantine metadata
    quarantined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    quarantined_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Review status
    review_status = Column(String(20), nullable=False, default="pending_review")  # 'pending_review', 'reviewed', 'auto_released'
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Auto-release
    auto_release_after = Column(DateTime(timezone=True), nullable=True)  # Timestamp for auto-release
    auto_release_reason = Column(String(255), nullable=True)
    
    # Additional metadata
    metadata = Column(JSONB, nullable=True)  # Additional quarantine metadata
    
    # Relationships
    tenant = relationship("Tenant")
    runbook = relationship("Runbook", backref="quarantines")
    runbook_version = relationship("RunbookVersion", backref="quarantines")
    quarantiner = relationship("User", foreign_keys=[quarantined_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    __table_args__ = (
        Index("idx_runbook_quarantines_runbook", "runbook_id"),
        Index("idx_runbook_quarantines_version", "runbook_version_id"),
        Index("idx_runbook_quarantines_status", "review_status"),
        Index("idx_runbook_quarantines_tenant", "tenant_id"),
        Index("idx_runbook_quarantines_quarantined_at", "quarantined_at"),
        # Unique constraint: one active quarantine per runbook version
        Index("idx_runbook_quarantines_unique", "runbook_id", "runbook_version_id", "review_status", unique=False),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RunbookQuarantine(id={self.id}, "
            f"runbook_id={self.runbook_id}, "
            f"version_id={self.runbook_version_id}, "
            f"reason='{self.quarantine_reason}', "
            f"status='{self.review_status}')>"
        )
