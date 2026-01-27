"""
RemediationAnalytics model for tracking remediation effectiveness metrics
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class RemediationAnalytics(Base):
    """
    Tracks remediation effectiveness analytics including MTTR, automation coverage, and ROI.
    
    Aggregates metrics over time periods to demonstrate value and identify improvement areas.
    """
    
    __tablename__ = "remediation_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    
    # MTTR (Mean Time To Resolution)
    mttr_minutes = Column(Numeric(10, 2), nullable=True)  # Average resolution time
    
    # Automation coverage
    automation_coverage_pct = Column(Numeric(5, 2), nullable=True)  # % of incidents handled automatically
    manual_intervention_count = Column(Integer, nullable=False, default=0)
    auto_resolution_count = Column(Integer, nullable=False, default=0)
    total_incidents = Column(Integer, nullable=False, default=0)
    
    # ROI metrics
    roi_metrics = Column(JSONB, nullable=True)  # {
    #   "cost_savings": 10000,
    #   "time_savings_hours": 50,
    #   "labor_cost_per_hour": 100,
    #   "total_value": 15000
    # }
    
    # Top failing steps
    top_failing_steps = Column(JSONB, nullable=True)  # [
    #   {"step_id": 1, "failure_count": 5, "error_type": "timeout"},
    #   {"step_id": 2, "failure_count": 3, "error_type": "connection_error"}
    # ]
    
    # Improvement trends
    improvement_trends = Column(JSONB, nullable=True)  # {
    #   "mttr_trend": [{"date": "...", "mttr": 30}, ...],
    #   "coverage_trend": [{"date": "...", "coverage": 80}, ...]
    # }
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("idx_remediation_analytics_tenant", "tenant_id"),
        Index("idx_remediation_analytics_period", "period_start", "period_end"),
        Index("idx_remediation_analytics_type", "period_type"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RemediationAnalytics(id={self.id}, "
            f"tenant_id={self.tenant_id}, "
            f"period_type='{self.period_type}', "
            f"mttr={self.mttr_minutes}min)>"
        )
