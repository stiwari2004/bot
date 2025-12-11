"""
DecisionAnalyticsRepository
Data access layer for DecisionAnalytics model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone

from app.repositories.base_repository import BaseRepository
from app.models.decision_analytics import DecisionAnalytics


class DecisionAnalyticsRepository(BaseRepository[DecisionAnalytics]):
    """Repository for DecisionAnalytics operations"""
    
    def __init__(self, db: Session):
        super().__init__(DecisionAnalytics, db)
    
    def get_by_period(
        self,
        tenant_id: int,
        period_type: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[DecisionAnalytics]:
        """Get analytics for a specific period"""
        return self.db.query(DecisionAnalytics).filter(
            DecisionAnalytics.tenant_id == tenant_id,
            DecisionAnalytics.period_type == period_type,
            DecisionAnalytics.period_start == period_start,
            DecisionAnalytics.period_end == period_end
        ).first()
    
    def get_recent_analytics(
        self,
        tenant_id: int,
        period_type: str,
        limit: int = 30
    ) -> List[DecisionAnalytics]:
        """Get recent analytics records"""
        return self.db.query(DecisionAnalytics).filter(
            DecisionAnalytics.tenant_id == tenant_id,
            DecisionAnalytics.period_type == period_type
        ).order_by(DecisionAnalytics.period_start.desc()).limit(limit).all()
    
    def get_latest_analytics(
        self,
        tenant_id: int,
        period_type: str
    ) -> Optional[DecisionAnalytics]:
        """Get the latest analytics record for a period type"""
        return self.db.query(DecisionAnalytics).filter(
            DecisionAnalytics.tenant_id == tenant_id,
            DecisionAnalytics.period_type == period_type
        ).order_by(DecisionAnalytics.period_start.desc()).first()








