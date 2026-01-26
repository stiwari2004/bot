"""
Super Admin Dashboard Service
Aggregates platform-wide metrics, revenue, usage, and trial data
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from app.core.logging import get_logger
from app.core.config import settings
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
from app.services.subscription.subscription_tracker import SubscriptionTracker

logger = get_logger(__name__)


class SuperAdminDashboardService:
    """Service for aggregating super admin dashboard data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.billing_calculator = BillingCalculator(db)
        self.billing_tracker = BillingTracker(db)
        self.subscription_tracker = SubscriptionTracker(db)
    
    def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive platform overview"""
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Basic counts
        total_tenants = self.db.query(Tenant).count()
        active_tenants = self.db.query(Tenant).filter(Tenant.is_active == True).count()
        
        # Count users
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        
        # Count nodes
        total_nodes = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.is_active == True
        ).count()
        
        # Get subscriptions
        subscriptions = self.db.query(TenantSubscription).filter(
            TenantSubscription.status == "active"
        ).all()
        
        # Plan distribution
        plan_distribution = {}
        trial_count = 0
        paid_count = 0
        
        for sub in subscriptions:
            if sub.license_plan_id:
                plan = self.db.query(LicensePlan).filter(LicensePlan.id == sub.license_plan_id).first()
                if plan:
                    plan_key = plan.plan_key
                    plan_distribution[plan_key] = plan_distribution.get(plan_key, 0) + 1
                    if plan_key == "trial":
                        trial_count += 1
                    else:
                        paid_count += 1
        
        # Count inactive tenants
        inactive_count = total_tenants - active_tenants
        
        # Revenue calculation (current month)
        revenue_data = self._calculate_current_month_revenue()
        
        # Usage metrics (current month)
        usage_data = self._get_current_month_usage()
        
        # Growth calculations
        last_month_tenants = self._count_tenants_for_period(last_month_start, current_month_start)
        tenant_growth = ((active_tenants - last_month_tenants) / last_month_tenants * 100) if last_month_tenants > 0 else 0
        
        last_month_users = self._count_users_for_period(last_month_start, current_month_start)
        user_growth = ((active_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 0
        
        last_month_nodes = self._count_nodes_for_period(last_month_start, current_month_start)
        node_growth = ((total_nodes - last_month_nodes) / last_month_nodes * 100) if last_month_nodes > 0 else 0
        
        # Alerts
        alerts = self._get_alerts()
        
        return {
            "summary": {
                "total_tenants": total_tenants,
                "active_tenants": active_tenants,
                "inactive_tenants": inactive_count,
                "trial_tenants": trial_count,
                "paid_tenants": paid_count,
                "total_users": total_users,
                "active_users": active_users,
                "total_nodes": total_nodes,
                "tenant_growth_percent": round(tenant_growth, 2),
                "user_growth_percent": round(user_growth, 2),
                "node_growth_percent": round(node_growth, 2),
            },
            "revenue": revenue_data,
            "usage": usage_data,
            "plan_distribution": plan_distribution,
            "alerts": alerts,
            "timestamp": now.isoformat()
        }
    
    def _calculate_current_month_revenue(self) -> Dict[str, Any]:
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
        # Get current month usage for all tenants
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
                # Assume included tokens are in plan, overage is what we charge
                # For now, use total LLM token cost as overage (simplified)
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
    
    def _get_current_month_usage(self) -> Dict[str, Any]:
        """Get current month usage metrics"""
        now = datetime.now(timezone.utc)
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Aggregate usage from TenantBillingUsage
        usage_records = self.db.query(TenantBillingUsage).filter(
            TenantBillingUsage.period_start == period_start
        ).all()
        
        total_tickets = sum(u.tickets_received for u in usage_records)
        total_executions = sum(u.execution_sessions for u in usage_records)
        total_api_calls = sum(u.api_calls for u in usage_records)
        total_llm_tokens = sum(u.llm_tokens for u in usage_records)
        
        # Get total nodes
        total_nodes = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.is_active == True
        ).count()
        
        return {
            "total_nodes": total_nodes,
            "total_llm_tokens": total_llm_tokens,  # in thousands
            "total_tickets": total_tickets,
            "total_executions": total_executions,
            "total_api_calls": total_api_calls
        }
    
    def _get_alerts(self) -> List[Dict[str, Any]]:
        """Get platform alerts and notifications"""
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Check for expiring trials
        expiring_soon = now + timedelta(days=7)
        expiring_count = self.db.query(TenantSubscription).join(
            LicensePlan, TenantSubscription.license_plan_id == LicensePlan.id
        ).filter(
            LicensePlan.plan_key == "trial",
            TenantSubscription.status == "active",
            TenantSubscription.expires_at.isnot(None),
            TenantSubscription.expires_at <= expiring_soon
        ).count()
        
        if expiring_count > 0:
            alerts.append({
                "type": "warning",
                "severity": "medium",
                "title": f"{expiring_count} trials expiring in 7 days",
                "message": "Some trial subscriptions are expiring soon",
                "action_required": True
            })
        
        # Check for tenants exceeding limits
        subscriptions_exceeding = self.db.query(TenantSubscription).filter(
            TenantSubscription.status == "active",
            or_(
                TenantSubscription.current_nodes > TenantSubscription.max_nodes,
                TenantSubscription.current_seats > TenantSubscription.max_seats
            )
        ).count()
        
        if subscriptions_exceeding > 0:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "title": f"{subscriptions_exceeding} tenants exceeding limits",
                "message": "Some tenants have exceeded their subscription limits",
                "action_required": True
            })
        
        # Send email notifications for critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical" or a.get("severity") == "high"]
        if critical_alerts:
            self._send_critical_alert_emails(critical_alerts)
        
        return alerts
    
    def _send_critical_alert_emails(self, alerts: List[Dict[str, Any]]) -> None:
        """Send email notifications to super admins for critical alerts"""
        try:
            from app.services.email_service import get_email_service
            from app.models.super_admin import SuperAdmin
            
            email_service = get_email_service()
            
            # Get all active super admins
            super_admins = self.db.query(SuperAdmin).filter(SuperAdmin.is_active == True).all()
            
            if not super_admins:
                logger.warning("No active super admins found for critical alert notifications")
                return
            
            # Build email content
            critical_count = len([a for a in alerts if a.get("severity") == "critical"])
            high_count = len([a for a in alerts if a.get("severity") == "high"])
            
            subject = f"🚨 Critical Platform Alert{'s' if len(alerts) > 1 else ''} - {critical_count + high_count} Issue{'s' if len(alerts) > 1 else ''} Detected"
            
            alerts_html = ""
            for alert in alerts:
                severity_color = "red" if alert.get("severity") == "critical" else "orange"
                alerts_html += f"""
                <div style="margin: 15px 0; padding: 15px; border-left: 4px solid {severity_color}; background-color: #f9f9f9;">
                    <h3 style="margin: 0 0 10px 0; color: {severity_color};">
                        {alert.get("title", "Alert")}
                    </h3>
                    <p style="margin: 0; color: #333;">
                        {alert.get("message", "")}
                    </p>
                    {f'<p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">Tenant ID: {alert.get("tenant_id", "N/A")}</p>' if alert.get("tenant_id") else ""}
                </div>
                """
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #dc2626; color: white; padding: 20px; border-radius: 4px 4px 0 0; }}
                    .content {{ background-color: white; padding: 20px; border: 1px solid #ddd; border-top: none; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #666; text-align: center; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">🚨 Critical Platform Alert</h2>
                    </div>
                    <div class="content">
                        <p>Dear Super Administrator,</p>
                        <p>The following critical alert{'s have' if len(alerts) > 1 else ' has'} been detected on the platform:</p>
                        {alerts_html}
                        <p style="margin-top: 30px;">
                            <a href="{settings.FRONTEND_BASE_URL}/super-admin" class="button">View Dashboard</a>
                        </p>
                    </div>
                    <div class="footer">
                        <p>This is an automated alert notification from the Resolvify Platform.</p>
                        <p>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Critical Platform Alert
            
            Dear Super Administrator,
            
            The following critical alert(s) have been detected on the platform:
            
            {chr(10).join([f"- {a.get('title', 'Alert')}: {a.get('message', '')}" for a in alerts])}
            
            Please log in to the dashboard to review and take action:
            {settings.FRONTEND_BASE_URL}/super-admin
            
            This is an automated alert notification.
            """
            
            # Send to all super admins
            for admin in super_admins:
                email_service.send_email(
                    to_email=admin.email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body
                )
                logger.info(f"Sent critical alert email to super admin: {admin.email}")
                
        except Exception as e:
            logger.error(f"Failed to send critical alert emails: {e}", exc_info=True)
    
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
    
    def get_tenants_list(
        self,
        skip: int = 0,
        limit: int = 100,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
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
    
    def get_revenue_analytics(
        self,
        months: int = 12
    ) -> Dict[str, Any]:
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
    
    def get_trial_analytics(self) -> Dict[str, Any]:
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
        current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # This is simplified - in reality, we'd track when a trial converts to paid
        # For now, count subscriptions that started as trial and now have a paid plan
        trials_converted = 0  # TODO: Implement proper conversion tracking
        
        return {
            "active_trials": active_trials,
            "trials_expiring_7_days": trials_expiring_7_days,
            "trials_expiring_30_days": trials_expiring_30_days,
            "trials_converted_this_month": trials_converted,
            "conversion_rate": round((trials_converted / active_trials * 100) if active_trials > 0 else 0, 2)
        }
