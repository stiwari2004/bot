"""
Revenue Aggregator for dashboard revenue calculations
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.tenant_subscription import TenantSubscription
from app.models.tenant_billing_config import TenantBillingConfig, TenantBillingUsage
from app.core.logging import get_logger

logger = get_logger(__name__)


class RevenueAggregator:
    """Aggregate revenue data for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_current_month_revenue(self) -> dict:
        """Calculate current month revenue breakdown"""
        now = datetime.now(timezone.utc)
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Get all active subscriptions
        subscriptions = self.db.query(TenantSubscription).filter(
            TenantSubscription.status == "active"
        ).all()
        
        fixed_revenue = Decimal(0)
        node_overage_revenue = Decimal(0)
        llm_overage_revenue = Decimal(0)
        
        # Calculate revenue from subscriptions
        for sub in subscriptions:
            fixed_revenue += Decimal(str(sub.monthly_price))
            
            # Calculate overage (if nodes exceeded)
            if sub.nodes_exceeded:
                overage_nodes = sub.current_nodes - sub.max_nodes
                node_overage_revenue += Decimal(str(sub.node_overage_rate)) * overage_nodes
        
        # Calculate LLM overage from billing usage
        usage_records = self.db.query(TenantBillingUsage).filter(
            TenantBillingUsage.period_start == period_start,
            TenantBillingUsage.status.in_(["calculated", "invoiced", "paid"])
        ).all()
        
        for usage in usage_records:
            # Get billing config to check LLM overage
            config = self.db.query(TenantBillingConfig).filter(
                TenantBillingConfig.tenant_id == usage.tenant_id,
                TenantBillingConfig.is_active == True
            ).first()
            
            if config and config.per_llm_token_enabled:
                llm_overage_revenue += Decimal(str(usage.llm_token_cost))
        
        total_revenue = fixed_revenue + node_overage_revenue + llm_overage_revenue
        
        # Estimate LLM costs (using average cost of ₹0.15 per 1K tokens)
        total_llm_tokens = sum(u.llm_tokens for u in usage_records)
        estimated_llm_costs = Decimal(str(total_llm_tokens)) * Decimal("0.15")
        
        # Calculate margin
        estimated_total_costs = estimated_llm_costs + Decimal("50000")  # Infrastructure estimate
        margin_percent = ((total_revenue - estimated_total_costs) / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "fixed_revenue": float(fixed_revenue),
            "node_overage_revenue": float(node_overage_revenue),
            "llm_overage_revenue": float(llm_overage_revenue),
            "total_revenue": float(total_revenue),
            "estimated_llm_costs": float(estimated_llm_costs),
            "estimated_total_costs": float(estimated_total_costs),
            "estimated_margin_percent": round(float(margin_percent), 2)
        }
    
    def get_revenue_analytics(self, months: int = 12) -> dict:
        """Get revenue analytics for specified number of months"""
        now = datetime.now(timezone.utc)
        revenue_by_month = []
        
        for i in range(months):
            month_date = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_start = month_date
            if month_date.month == 12:
                period_end = datetime(month_date.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                period_end = datetime(month_date.year, month_date.month + 1, 1, tzinfo=timezone.utc)
            
            # Get revenue for this period
            usage_records = self.db.query(TenantBillingUsage).filter(
                TenantBillingUsage.period_start == period_start,
                TenantBillingUsage.period_end == period_end
            ).all()
            
            total_revenue = sum(float(u.total_cost) for u in usage_records)
            
            revenue_by_month.append({
                "month": period_start.strftime("%Y-%m"),
                "revenue": total_revenue,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            })
        
        revenue_by_month.reverse()  # Oldest first
        
        # Calculate growth
        if len(revenue_by_month) >= 2:
            current_revenue = revenue_by_month[-1]["revenue"]
            previous_revenue = revenue_by_month[-2]["revenue"]
            growth_percent = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        else:
            growth_percent = 0
        
        return {
            "revenue_by_month": revenue_by_month,
            "total_revenue": sum(r["revenue"] for r in revenue_by_month),
            "average_monthly_revenue": sum(r["revenue"] for r in revenue_by_month) / len(revenue_by_month) if revenue_by_month else 0,
            "growth_percent": round(growth_percent, 2)
        }
