"""
RunbookMetrics model for caching runbook quality metrics
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RunbookMetrics(Base):
    """
    Cached metrics for runbook performance and quality.
    
    This table stores pre-calculated metrics to avoid expensive
    queries on every request. Metrics are updated periodically
    or on execution completion.
    """
    
    __tablename__ = "runbook_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Execution metrics
    total_executions = Column(Integer, nullable=False, default=0)
    successful_executions = Column(Integer, nullable=False, default=0)
    failed_executions = Column(Integer, nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    
    # Time metrics
    avg_execution_time_minutes = Column(Numeric(10, 2), nullable=True)
    min_execution_time_minutes = Column(Numeric(10, 2), nullable=True)
    max_execution_time_minutes = Column(Numeric(10, 2), nullable=True)
    
    # Quality metrics
    avg_rating = Column(Numeric(3, 2), nullable=True)  # Average feedback rating (1-5)
    issue_resolution_rate = Column(Numeric(5, 2), nullable=True)  # % of issues resolved
    step_completion_rate = Column(Numeric(5, 2), nullable=True)  # % of steps completed
    rollback_frequency = Column(Numeric(5, 2), nullable=True)  # % of executions that rolled back
    
    # Metadata
    last_calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    calculation_period_days = Column(Integer, nullable=False, default=30)  # Days used for calculation
    
    # Relationships
    runbook = relationship("Runbook", backref="metrics")
    
    __table_args__ = (
        Index("idx_runbook_metrics_runbook", "runbook_id"),
        Index("idx_runbook_metrics_tenant", "tenant_id"),
        Index("idx_runbook_metrics_success", "success_rate"),
        Index("idx_runbook_metrics_calculated", "last_calculated_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RunbookMetrics(id={self.id}, "
            f"runbook_id={self.runbook_id}, "
            f"success_rate={self.success_rate}, "
            f"total_executions={self.total_executions})>"
        )

