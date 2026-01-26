"""
Growth Calculator for dashboard metrics
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.credential import InfrastructureConnection
from app.core.logging import get_logger

logger = get_logger(__name__)


class GrowthCalculator:
    """Calculate growth metrics for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_tenant_growth(self, current_count: int, last_month_start: datetime, current_month_start: datetime) -> float:
        """Calculate tenant growth percentage"""
        last_month_count = self._count_tenants_for_period(last_month_start, current_month_start)
        return round(((current_count - last_month_count) / last_month_count * 100) if last_month_count > 0 else 0, 2)
    
    def calculate_user_growth(self, current_count: int, last_month_start: datetime, current_month_start: datetime) -> float:
        """Calculate user growth percentage"""
        last_month_count = self._count_users_for_period(last_month_start, current_month_start)
        return round(((current_count - last_month_count) / last_month_count * 100) if last_month_count > 0 else 0, 2)
    
    def calculate_node_growth(self, current_count: int, last_month_start: datetime, current_month_start: datetime) -> float:
        """Calculate node growth percentage"""
        last_month_count = self._count_nodes_for_period(last_month_start, current_month_start)
        return round(((current_count - last_month_count) / last_month_count * 100) if last_month_count > 0 else 0, 2)
    
    def _count_tenants_for_period(self, start: datetime, end: datetime) -> int:
        """Count tenants created in period"""
        return self.db.query(Tenant).filter(
            Tenant.created_at >= start,
            Tenant.created_at < end
        ).count()
    
    def _count_users_for_period(self, start: datetime, end: datetime) -> int:
        """Count users created in period"""
        return self.db.query(User).filter(
            User.created_at >= start,
            User.created_at < end
        ).count()
    
    def _count_nodes_for_period(self, start: datetime, end: datetime) -> int:
        """Count nodes created in period"""
        return self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.created_at >= start,
            InfrastructureConnection.created_at < end
        ).count()
