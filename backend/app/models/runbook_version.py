"""
RunbookVersion model for tracking runbook version history
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RunbookVersion(Base):
    """
    Tracks version history for runbooks.
    
    Each time a runbook is updated, a new version record is created
    to maintain a complete history of changes.
    """
    
    __tablename__ = "runbook_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Version information
    version_number = Column(String(20), nullable=False)  # e.g., "1.0.0", "1.1.0"
    parent_version_id = Column(
        Integer, ForeignKey("runbook_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # Version metadata
    title = Column(String(255), nullable=False)
    body_md = Column(Text, nullable=True)  # Full runbook content at this version
    body_yaml = Column(Text, nullable=True)  # YAML content if available
    
    # Change tracking
    change_summary = Column(Text, nullable=True)  # Human-readable summary of changes
    change_type = Column(String(50), nullable=True)  # 'major', 'minor', 'patch', 'custom'
    
    # Metadata
    created_by = Column(Integer, nullable=True)  # User ID who created this version
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Status
    is_current = Column(String(10), nullable=False, default='false')  # 'true' or 'false'
    
    # Relationships
    runbook = relationship("Runbook", backref="versions")
    parent_version = relationship("RunbookVersion", remote_side=[id], backref="child_versions")
    
    __table_args__ = (
        Index("idx_runbook_versions_runbook", "runbook_id"),
        Index("idx_runbook_versions_version", "version_number"),
        Index("idx_runbook_versions_current", "is_current"),
        Index("idx_runbook_versions_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RunbookVersion(id={self.id}, "
            f"runbook_id={self.runbook_id}, "
            f"version='{self.version_number}', "
            f"is_current={self.is_current})>"
        )








