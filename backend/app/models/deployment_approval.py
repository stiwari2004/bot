"""
Deployment Approval model for tracking code and runbook promotions
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DeploymentApproval(Base):
    """Tracks approval requests for promoting changes from dev to production"""
    __tablename__ = "deployment_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_type = Column(String(50), nullable=False)  # 'code' or 'runbook'
    target_environment = Column(String(20), nullable=False, default="production")  # 'production'
    reference_id = Column(Integer, nullable=True)  # runbook_id or commit reference
    reference_name = Column(String(500), nullable=True)  # Human-readable name
    status = Column(String(20), default="pending")  # pending, approved, rejected, deployed
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    deployment_log = Column(Text, nullable=True)
    # Use 'name' parameter to map Python attribute to database column
    # This allows backward compatibility: Python uses 'approval_metadata' (avoids SQLAlchemy reserved word)
    # Database can use either 'metadata' (existing) or 'approval_metadata' (new)
    approval_metadata = Column("metadata", JSON, nullable=True)  # Additional metadata (diffs, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_deployment_approvals_type', 'deployment_type'),
        Index('idx_deployment_approvals_status', 'status'),
        Index('idx_deployment_approvals_requested_by', 'requested_by'),
        Index('idx_deployment_approvals_approved_by', 'approved_by'),
        Index('idx_deployment_approvals_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<DeploymentApproval(id={self.id}, type='{self.deployment_type}', status='{self.status}')>"

