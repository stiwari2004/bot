"""
Overview Aggregator for dashboard summary data
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.credential import InfrastructureConnection
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.core.logging import get_logger

logger = get_logger(__name__)


class OverviewAggregator:
    """Aggregate overview/summary data for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_summary(self) -> dict:
        """Get platform summary metrics"""
        # Basic counts
        total_tenants = self.db.query(Tenant).count()
        active_tenants = self.db.query(Tenant).filter(Tenant.is_active == True).count()
        inactive_tenants = total_tenants - active_tenants
        
        # Count users
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        
        # Count nodes
        total_nodes = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.is_active == True
        ).count()
        
        # Get subscriptions and plan distribution
        subscriptions = self.db.query(TenantSubscription).filter(
            TenantSubscription.status == "active"
        ).all()
        
        # Batch fetch all plans to avoid N+1 queries
        plan_ids = [sub.license_plan_id for sub in subscriptions if sub.license_plan_id]
        plans = {}
        if plan_ids:
            plans_query = self.db.query(LicensePlan).filter(LicensePlan.id.in_(plan_ids)).all()
            plans = {plan.id: plan for plan in plans_query}
        
        plan_distribution = {}
        trial_count = 0
        paid_count = 0
        
        for sub in subscriptions:
            if sub.license_plan_id and sub.license_plan_id in plans:
                plan = plans[sub.license_plan_id]
                plan_key = plan.plan_key
                plan_distribution[plan_key] = plan_distribution.get(plan_key, 0) + 1
                if plan_key == "trial":
                    trial_count += 1
                else:
                    paid_count += 1
        
        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "inactive_tenants": inactive_tenants,
            "trial_tenants": trial_count,
            "paid_tenants": paid_count,
            "total_users": total_users,
            "active_users": active_users,
            "total_nodes": total_nodes,
            "plan_distribution": plan_distribution
        }
