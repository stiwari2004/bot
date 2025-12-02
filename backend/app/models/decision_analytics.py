"""
DecisionAnalytics model for tracking decision engine performance and accuracy
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class DecisionAnalytics(Base):
    """
    Tracks decision engine performance metrics and accuracy.
    
    This model stores aggregated analytics about decision quality,
    recommendation acceptance, pattern matching accuracy, etc.
    """
    
    __tablename__ = "decision_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Time period for this analytics record
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    
    # Recommendation metrics
    total_recommendations = Column(Integer, nullable=False, default=0)
    accepted_recommendations = Column(Integer, nullable=False, default=0)
    rejected_recommendations = Column(Integer, nullable=False, default=0)
    recommendation_acceptance_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    
    # Pattern matching metrics
    total_pattern_searches = Column(Integer, nullable=False, default=0)
    successful_pattern_matches = Column(Integer, nullable=False, default=0)
    pattern_match_accuracy = Column(Numeric(5, 2), nullable=False, default=0.0)
    avg_pattern_match_confidence = Column(Numeric(5, 2), nullable=True)
    
    # Confidence score distribution
    high_confidence_count = Column(Integer, nullable=False, default=0)  # >= 0.8
    medium_confidence_count = Column(Integer, nullable=False, default=0)  # 0.5-0.8
    low_confidence_count = Column(Integer, nullable=False, default=0)  # < 0.5
    avg_confidence_score = Column(Numeric(5, 2), nullable=True)
    
    # Decision outcome tracking
    auto_execute_count = Column(Integer, nullable=False, default=0)
    manual_execute_count = Column(Integer, nullable=False, default=0)
    escalation_count = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_decision_time_seconds = Column(Numeric(10, 2), nullable=True)
    avg_recommendation_time_seconds = Column(Numeric(10, 2), nullable=True)
    
    # Outcome tracking
    successful_resolutions = Column(Integer, nullable=False, default=0)
    failed_resolutions = Column(Integer, nullable=False, default=0)
    resolution_success_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    
    # Additional metadata
    meta_data = Column(JSONB, nullable=True)  # Additional analytics data
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index("idx_decision_analytics_tenant", "tenant_id"),
        Index("idx_decision_analytics_period", "period_start", "period_end"),
        Index("idx_decision_analytics_type", "period_type"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DecisionAnalytics(id={self.id}, "
            f"tenant_id={self.tenant_id}, "
            f"period_type='{self.period_type}', "
            f"acceptance_rate={self.recommendation_acceptance_rate}%)>"
        )

