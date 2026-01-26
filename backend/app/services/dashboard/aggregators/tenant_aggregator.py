"""
Tenant Aggregator for dashboard tenant data
"""
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.models.tenant_billing_config import TenantBillingUsage
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.core.logging import get_logger

logger = get_logger(__name__)


class TenantAggregator:
    """Aggregate tenant data for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
        self.subscription_tracker = SubscriptionTracker(db)
    
    def get_tenants_list(
        self,
        skip: int = 0,
        limit: int = 100,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, any]:
        """Get paginated list of tenants with usage data"""
        query = self.db.query(Tenant)
        
        # Apply filters
        if status_filter == "active":
            query = query.filter(Tenant.is_active == True)
        elif status_filter == "inactive":
            query = query.filter(Tenant.is_active == False)
        
        if search:
            query = query.filter(
                or_(
                    Tenant.name.ilike(f"%{search}%"),
                    Tenant.contact_email.ilike(f"%{search}%")
                )
            )
        
        total_count = query.count()
        tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()
        
        # Enrich with subscription and usage data
        tenant_list = []
        for tenant in tenants:
            subscription = self.subscription_tracker.get_subscription(tenant.id)
            plan_name = "None"
            plan_key = None
            nodes_used = 0
            nodes_limit = 0
            llm_tokens = 0
            revenue = 0.0
            
            if subscription:
                if subscription.license_plan_id:
                    plan = self.db.query(LicensePlan).filter(LicensePlan.id == subscription.license_plan_id).first()
                    if plan:
                        plan_name = plan.plan_name
                        plan_key = plan.plan_key
                
                nodes_used = subscription.current_nodes
                nodes_limit = subscription.max_nodes
                revenue = float(subscription.monthly_price)
            
            # Get current month LLM tokens
            now = datetime.now(timezone.utc)
            period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            usage = self.db.query(TenantBillingUsage).filter(
                TenantBillingUsage.tenant_id == tenant.id,
                TenantBillingUsage.period_start == period_start
            ).first()
            
            if usage:
                llm_tokens = usage.llm_tokens
            
            tenant_list.append({
                "id": tenant.id,
                "name": tenant.name,
                "subdomain_slug": tenant.subdomain_slug,
                "contact_email": tenant.contact_email,
                "is_active": tenant.is_active,
                "plan_name": plan_name,
                "plan_key": plan_key,
                "nodes_used": nodes_used,
                "nodes_limit": nodes_limit,
                "llm_tokens": llm_tokens,
                "revenue": revenue,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None
            })
        
        # Apply plan filter after enrichment
        if plan_filter:
            tenant_list = [t for t in tenant_list if t["plan_key"] == plan_filter]
        
        return {
            "tenants": tenant_list,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    
    def get_trial_analytics(self) -> Dict[str, any]:
        """Get trial subscription analytics"""
        now = datetime.now(timezone.utc)
        
        # Get trial plan
        trial_plan = self.db.query(LicensePlan).filter(LicensePlan.plan_key == "trial").first()
        
        if not trial_plan:
            return {
                "active_trials": 0,
                "trials_expiring_7_days": 0,
                "trials_expiring_30_days": 0,
                "trials_converted_this_month": 0,
                "conversion_rate": 0.0
            }
        
        # Active trials
        active_trials = self.db.query(TenantSubscription).filter(
            TenantSubscription.license_plan_id == trial_plan.id,
            TenantSubscription.status == "active"
        ).count()
        
        # Expiring soon
        from datetime import timedelta
        expiring_7_days = now + timedelta(days=7)
        expiring_30_days = now + timedelta(days=30)
        
        trials_expiring_7_days = self.db.query(TenantSubscription).filter(
            TenantSubscription.license_plan_id == trial_plan.id,
            TenantSubscription.status == "active",
            TenantSubscription.expires_at.isnot(None),
            TenantSubscription.expires_at <= expiring_7_days
        ).count()
        
        trials_expiring_30_days = self.db.query(TenantSubscription).filter(
            TenantSubscription.license_plan_id == trial_plan.id,
            TenantSubscription.status == "active",
            TenantSubscription.expires_at.isnot(None),
            TenantSubscription.expires_at <= expiring_30_days
        ).count()
        
        # Conversions this month
        # This is simplified - in reality, we'd track when a trial converts to paid
        trials_converted = 0  # TODO: Implement proper conversion tracking
        
        return {
            "active_trials": active_trials,
            "trials_expiring_7_days": trials_expiring_7_days,
            "trials_expiring_30_days": trials_expiring_30_days,
            "trials_converted_this_month": trials_converted,
            "conversion_rate": round((trials_converted / active_trials * 100) if active_trials > 0 else 0, 2)
        }
