"""
Tenant Admin Dashboard Service
Aggregates tenant-level metrics, usage, and analytics
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.models.tenant_subscription import TenantSubscription
from app.models.tenant_billing_config import TenantBillingConfig, TenantBillingUsage
from app.models.license_plan import LicensePlan
from app.models.credential import InfrastructureConnection
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession
from app.services.billing.billing_calculator import BillingCalculator
from app.services.billing.billing_tracker import BillingTracker

logger = get_logger(__name__)


class TenantAdminDashboardService:
    """Service for aggregating tenant admin dashboard data"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.billing_calculator = BillingCalculator(db)
        self.billing_tracker = BillingTracker(db)
    
    def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive tenant overview"""
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Get tenant
        tenant = self.db.query(Tenant).filter(Tenant.id == self.tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        # Count users
        total_users = self.db.query(User).filter(User.tenant_id == self.tenant_id).count()
        active_users = self.db.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.is_active == True
        ).count()
        
        # Count nodes
        total_nodes = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id == self.tenant_id,
            InfrastructureConnection.is_active == True
        ).count()
        
        # Get subscription
        subscription = self.db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == self.tenant_id,
            TenantSubscription.status == "active"
        ).first()
        
        plan_name = "No Plan"
        plan_key = None
        nodes_limit = 0
        seats_limit = 0
        nodes_used = 0
        seats_used = 0
        
        if subscription:
            if subscription.license_plan_id:
                plan = self.db.query(LicensePlan).filter(LicensePlan.id == subscription.license_plan_id).first()
                if plan:
                    plan_name = plan.name
                    plan_key = plan.plan_key
            
            nodes_limit = subscription.max_nodes or 0
            seats_limit = subscription.max_seats or 0
            nodes_used = subscription.current_nodes or 0
            seats_used = subscription.current_seats or 0
        
        # Usage metrics (current month)
        usage_data = self._get_current_month_usage()
        
        # Revenue/cost calculation (current month)
        billing_data = self._calculate_current_month_billing()
        
        # Alerts
        alerts = self._get_alerts(subscription)
        
        return {
            "summary": {
                "tenant_name": tenant.name,
                "tenant_id": tenant.id,
                "total_users": total_users,
                "active_users": active_users,
                "total_nodes": total_nodes,
                "plan_name": plan_name,
                "plan_key": plan_key,
                "nodes_used": nodes_used,
                "nodes_limit": nodes_limit,
                "seats_used": seats_used,
                "seats_limit": seats_limit,
                "nodes_utilization_percent": round((nodes_used / nodes_limit * 100) if nodes_limit > 0 else 0, 1),
                "seats_utilization_percent": round((seats_used / seats_limit * 100) if seats_limit > 0 else 0, 1),
            },
            "usage": usage_data,
            "billing": billing_data,
            "alerts": alerts,
            "timestamp": now.isoformat()
        }
    
    def _get_current_month_usage(self) -> Dict[str, Any]:
        """Get current month usage metrics"""
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Count executions
        total_executions = self.db.query(ExecutionSession).filter(
            ExecutionSession.tenant_id == self.tenant_id,
            ExecutionSession.created_at >= current_month_start
        ).count()
        
        # Count tickets
        total_tickets = self.db.query(Ticket).filter(
            Ticket.tenant_id == self.tenant_id,
            Ticket.created_at >= current_month_start
        ).count()
        
        # Get LLM tokens and API calls from billing usage
        billing_usage = self.db.query(TenantBillingUsage).filter(
            TenantBillingUsage.tenant_id == self.tenant_id,
            TenantBillingUsage.period_start >= current_month_start
        ).all()
        
        total_llm_tokens = sum(usage.llm_tokens_used or 0 for usage in billing_usage)
        total_api_calls = sum(usage.api_calls_count or 0 for usage in billing_usage)
        
        return {
            "total_executions": total_executions,
            "total_tickets": total_tickets,
            "total_llm_tokens": total_llm_tokens,
            "total_api_calls": total_api_calls
        }
    
    def _calculate_current_month_billing(self) -> Dict[str, Any]:
        """Calculate current month billing/costs"""
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Get subscription
        subscription = self.db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == self.tenant_id,
            TenantSubscription.status == "active"
        ).first()
        
        if not subscription:
            return {
                "monthly_cost": 0,
                "overage_cost": 0,
                "total_cost": 0,
                "estimated_llm_cost": 0
            }
        
        # Calculate billing
        try:
            billing_result = self.billing_calculator.calculate_monthly_billing(
                tenant_id=self.tenant_id,
                period_start=current_month_start,
                period_end=now
            )
            
            return {
                "monthly_cost": float(billing_result.get("fixed_cost", 0)),
                "node_overage_cost": float(billing_result.get("node_overage_cost", 0)),
                "llm_overage_cost": float(billing_result.get("llm_overage_cost", 0)),
                "total_cost": float(billing_result.get("total_cost", 0)),
                "estimated_llm_cost": float(billing_result.get("estimated_llm_cost", 0))
            }
        except Exception as e:
            logger.error(f"Error calculating billing for tenant {self.tenant_id}: {e}", exc_info=True)
            return {
                "monthly_cost": 0,
                "overage_cost": 0,
                "total_cost": 0,
                "estimated_llm_cost": 0
            }
    
    def _get_alerts(self, subscription: Optional[TenantSubscription]) -> List[Dict[str, Any]]:
        """Get tenant alerts and notifications"""
        alerts = []
        
        if not subscription:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "title": "No active subscription",
                "message": "Your tenant does not have an active subscription",
                "action_required": True
            })
            return alerts
        
        # Check for limits exceeded
        if subscription.current_nodes > subscription.max_nodes:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "title": "Node limit exceeded",
                "message": f"Using {subscription.current_nodes} nodes, limit is {subscription.max_nodes}",
                "action_required": True
            })
        
        if subscription.current_seats > subscription.max_seats:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "title": "Seat limit exceeded",
                "message": f"Using {subscription.current_seats} seats, limit is {subscription.max_seats}",
                "action_required": True
            })
        
        # Check for expiring subscription
        if subscription.expires_at:
            days_until_expiry = (subscription.expires_at - datetime.now(timezone.utc)).days
            if days_until_expiry <= 7:
                alerts.append({
                    "type": "warning",
                    "severity": "medium",
                    "title": f"Subscription expiring in {days_until_expiry} days",
                    "message": "Your subscription will expire soon. Please renew to avoid service interruption.",
                    "action_required": True
                })
        
        return alerts
