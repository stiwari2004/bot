"""
RunbookMetricsRepository
Data access layer for RunbookMetrics model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.runbook_metrics import RunbookMetrics


class RunbookMetricsRepository(BaseRepository[RunbookMetrics]):
    """Repository for RunbookMetrics operations"""
    
    def __init__(self, db: Session):
        super().__init__(RunbookMetrics, db)
    
    def get_by_runbook(
        self, 
        runbook_id: int, 
        tenant_id: Optional[int] = None
    ) -> Optional[RunbookMetrics]:
        """Get metrics for a specific runbook"""
        query = self.db.query(RunbookMetrics).filter(
            RunbookMetrics.runbook_id == runbook_id
        )
        if tenant_id:
            query = query.filter(RunbookMetrics.tenant_id == tenant_id)
        return query.first()
    
    def get_all_for_tenant(
        self, 
        tenant_id: int,
        min_success_rate: Optional[float] = None,
        limit: int = 100
    ) -> List[RunbookMetrics]:
        """Get all metrics for a tenant, optionally filtered by success rate"""
        query = self.db.query(RunbookMetrics).filter(
            RunbookMetrics.tenant_id == tenant_id
        )
        if min_success_rate is not None:
            query = query.filter(RunbookMetrics.success_rate >= min_success_rate)
        return query.order_by(RunbookMetrics.success_rate.desc()).limit(limit).all()
    
    def get_top_performers(
        self,
        tenant_id: int,
        limit: int = 10
    ) -> List[RunbookMetrics]:
        """Get top performing runbooks by success rate"""
        return self.db.query(RunbookMetrics).filter(
            RunbookMetrics.tenant_id == tenant_id,
            RunbookMetrics.total_executions >= 3  # At least 3 executions
        ).order_by(
            RunbookMetrics.success_rate.desc(),
            RunbookMetrics.total_executions.desc()
        ).limit(limit).all()
    
    def get_needs_attention(
        self,
        tenant_id: int,
        max_success_rate: float = 50.0,
        limit: int = 10
    ) -> List[RunbookMetrics]:
        """Get runbooks that need attention (low success rate)"""
        return self.db.query(RunbookMetrics).filter(
            RunbookMetrics.tenant_id == tenant_id,
            RunbookMetrics.success_rate < max_success_rate,
            RunbookMetrics.total_executions >= 2  # At least 2 executions
        ).order_by(
            RunbookMetrics.success_rate.asc(),
            RunbookMetrics.total_executions.desc()
        ).limit(limit).all()








