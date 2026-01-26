"""
Super Admin Dashboard Service
Aggregates platform-wide metrics, revenue, usage, and trial data
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.billing.billing_calculator import BillingCalculator
from app.services.billing.billing_tracker import BillingTracker
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.services.dashboard.aggregators import (
    OverviewAggregator,
    RevenueAggregator,
    UsageAggregator,
    AlertAggregator,
    TenantAggregator,
    GrowthCalculator
)

logger = get_logger(__name__)


class SuperAdminDashboardService:
    """Service for aggregating super admin dashboard data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.billing_calculator = BillingCalculator(db)
        self.billing_tracker = BillingTracker(db)
        self.subscription_tracker = SubscriptionTracker(db)
        
        # Initialize aggregators
        self.overview_aggregator = OverviewAggregator(db)
        self.revenue_aggregator = RevenueAggregator(db)
        self.usage_aggregator = UsageAggregator(db)
        self.alert_aggregator = AlertAggregator(db)
        self.tenant_aggregator = TenantAggregator(db)
        self.growth_calculator = GrowthCalculator(db)
    
    def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive platform overview"""
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Get summary data
        summary_data = self.overview_aggregator.get_summary()
        
        # Calculate growth metrics
        tenant_growth = self.growth_calculator.calculate_tenant_growth(
            summary_data["active_tenants"],
            last_month_start,
            current_month_start
        )
        user_growth = self.growth_calculator.calculate_user_growth(
            summary_data["active_users"],
            last_month_start,
            current_month_start
        )
        node_growth = self.growth_calculator.calculate_node_growth(
            summary_data["total_nodes"],
            last_month_start,
            current_month_start
        )
        
        # Add growth percentages to summary
        summary_data.update({
            "tenant_growth_percent": tenant_growth,
            "user_growth_percent": user_growth,
            "node_growth_percent": node_growth
        })
        
        # Get revenue and usage data
        revenue_data = self.revenue_aggregator.calculate_current_month_revenue()
        usage_data = self.usage_aggregator.get_current_month_usage()
        
        # Get alerts
        alerts = self.alert_aggregator.get_alerts()
        
        return {
            "summary": summary_data,
            "revenue": revenue_data,
            "usage": usage_data,
            "plan_distribution": summary_data["plan_distribution"],
            "alerts": alerts,
            "timestamp": now.isoformat()
        }
    
    def get_tenants_list(
        self,
        skip: int = 0,
        limit: int = 100,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of tenants with usage data"""
        return self.tenant_aggregator.get_tenants_list(
            skip=skip,
            limit=limit,
            plan_filter=plan_filter,
            status_filter=status_filter,
            search=search
        )
    
    def get_revenue_analytics(
        self,
        months: int = 12
    ) -> Dict[str, Any]:
        """Get revenue analytics for specified number of months"""
        return self.revenue_aggregator.get_revenue_analytics(months=months)
    
    def get_trial_analytics(self) -> Dict[str, Any]:
        """Get trial subscription analytics"""
        return self.tenant_aggregator.get_trial_analytics()
