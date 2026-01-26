"""
Dashboard Snapshot Service
Populates read models (snapshot tables) for fast dashboard queries
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.logging import get_logger
from app.services.dashboard.tenant_admin_dashboard_service import TenantAdminDashboardService
from app.services.dashboard.super_admin_dashboard_service import SuperAdminDashboardService
from app.services.connector_health_service import ConnectorHealthService

logger = get_logger(__name__)


class DashboardSnapshotService:
    """Service for populating dashboard snapshot tables"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_tenant_hourly_snapshot(self, tenant_id: int) -> None:
        """Create hourly snapshot for a tenant"""
        try:
            now = datetime.now(timezone.utc)
            snapshot_hour = now.replace(minute=0, second=0, microsecond=0)
            
            # Get current dashboard data
            service = TenantAdminDashboardService(self.db, tenant_id)
            overview = service.get_overview()
            
            # Insert snapshot
            self.db.execute(
                text("""
                    INSERT INTO tenant_dashboard_hourly_snapshot 
                    (tenant_id, snapshot_hour, total_users, active_users, total_nodes, 
                     plan_name, nodes_used, nodes_limit, total_executions, total_tickets,
                     total_llm_tokens, total_api_calls, monthly_cost, overage_cost, total_cost)
                    VALUES 
                    (:tenant_id, :snapshot_hour, :total_users, :active_users, :total_nodes,
                     :plan_name, :nodes_used, :nodes_limit, :total_executions, :total_tickets,
                     :total_llm_tokens, :total_api_calls, :monthly_cost, :overage_cost, :total_cost)
                    ON CONFLICT (tenant_id, snapshot_hour) 
                    DO UPDATE SET
                        total_users = EXCLUDED.total_users,
                        active_users = EXCLUDED.active_users,
                        total_nodes = EXCLUDED.total_nodes,
                        plan_name = EXCLUDED.plan_name,
                        nodes_used = EXCLUDED.nodes_used,
                        nodes_limit = EXCLUDED.nodes_limit,
                        total_executions = EXCLUDED.total_executions,
                        total_tickets = EXCLUDED.total_tickets,
                        total_llm_tokens = EXCLUDED.total_llm_tokens,
                        total_api_calls = EXCLUDED.total_api_calls,
                        monthly_cost = EXCLUDED.monthly_cost,
                        overage_cost = EXCLUDED.overage_cost,
                        total_cost = EXCLUDED.total_cost
                """),
                {
                    "tenant_id": tenant_id,
                    "snapshot_hour": snapshot_hour,
                    "total_users": overview.get("summary", {}).get("total_users", 0),
                    "active_users": overview.get("summary", {}).get("active_users", 0),
                    "total_nodes": overview.get("summary", {}).get("total_nodes", 0),
                    "plan_name": overview.get("summary", {}).get("plan_name"),
                    "nodes_used": overview.get("summary", {}).get("nodes_used", 0),
                    "nodes_limit": overview.get("summary", {}).get("nodes_limit", 0),
                    "total_executions": overview.get("usage", {}).get("total_executions", 0),
                    "total_tickets": overview.get("usage", {}).get("total_tickets", 0),
                    "total_llm_tokens": overview.get("usage", {}).get("total_llm_tokens", 0),
                    "total_api_calls": overview.get("usage", {}).get("total_api_calls", 0),
                    "monthly_cost": overview.get("billing", {}).get("monthly_cost", 0),
                    "overage_cost": overview.get("billing", {}).get("node_overage_cost", 0) + overview.get("billing", {}).get("llm_overage_cost", 0),
                    "total_cost": overview.get("billing", {}).get("total_cost", 0),
                }
            )
            self.db.commit()
            logger.info(f"Created hourly snapshot for tenant {tenant_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating tenant hourly snapshot: {e}", exc_info=True)
            raise
    
    def create_platform_daily_snapshot(self) -> None:
        """Create daily snapshot for platform dashboard"""
        try:
            now = datetime.now(timezone.utc)
            snapshot_date = now.date()
            
            # Get current dashboard data
            service = SuperAdminDashboardService(self.db)
            overview = service.get_overview()
            
            import json
            
            # Insert snapshot
            self.db.execute(
                text("""
                    INSERT INTO platform_dashboard_daily_snapshot 
                    (snapshot_date, total_tenants, active_tenants, inactive_tenants, trial_tenants, paid_tenants,
                     total_users, active_users, total_nodes, tenant_growth_percent, user_growth_percent, 
                     node_growth_percent, total_revenue, fixed_revenue, node_overage_revenue, llm_overage_revenue,
                     estimated_margin_percent, total_executions, total_tickets, total_llm_tokens, total_api_calls,
                     plan_distribution)
                    VALUES 
                    (:snapshot_date, :total_tenants, :active_tenants, :inactive_tenants, :trial_tenants, :paid_tenants,
                     :total_users, :active_users, :total_nodes, :tenant_growth_percent, :user_growth_percent,
                     :node_growth_percent, :total_revenue, :fixed_revenue, :node_overage_revenue, :llm_overage_revenue,
                     :estimated_margin_percent, :total_executions, :total_tickets, :total_llm_tokens, :total_api_calls,
                     :plan_distribution::jsonb)
                    ON CONFLICT (snapshot_date) 
                    DO UPDATE SET
                        total_tenants = EXCLUDED.total_tenants,
                        active_tenants = EXCLUDED.active_tenants,
                        inactive_tenants = EXCLUDED.inactive_tenants,
                        trial_tenants = EXCLUDED.trial_tenants,
                        paid_tenants = EXCLUDED.paid_tenants,
                        total_users = EXCLUDED.total_users,
                        active_users = EXCLUDED.active_users,
                        total_nodes = EXCLUDED.total_nodes,
                        tenant_growth_percent = EXCLUDED.tenant_growth_percent,
                        user_growth_percent = EXCLUDED.user_growth_percent,
                        node_growth_percent = EXCLUDED.node_growth_percent,
                        total_revenue = EXCLUDED.total_revenue,
                        fixed_revenue = EXCLUDED.fixed_revenue,
                        node_overage_revenue = EXCLUDED.node_overage_revenue,
                        llm_overage_revenue = EXCLUDED.llm_overage_revenue,
                        estimated_margin_percent = EXCLUDED.estimated_margin_percent,
                        total_executions = EXCLUDED.total_executions,
                        total_tickets = EXCLUDED.total_tickets,
                        total_llm_tokens = EXCLUDED.total_llm_tokens,
                        total_api_calls = EXCLUDED.total_api_calls,
                        plan_distribution = EXCLUDED.plan_distribution
                """),
                {
                    "snapshot_date": snapshot_date,
                    "total_tenants": overview.get("summary", {}).get("total_tenants", 0),
                    "active_tenants": overview.get("summary", {}).get("active_tenants", 0),
                    "inactive_tenants": overview.get("summary", {}).get("inactive_tenants", 0),
                    "trial_tenants": overview.get("summary", {}).get("trial_tenants", 0),
                    "paid_tenants": overview.get("summary", {}).get("paid_tenants", 0),
                    "total_users": overview.get("summary", {}).get("total_users", 0),
                    "active_users": overview.get("summary", {}).get("active_users", 0),
                    "total_nodes": overview.get("summary", {}).get("total_nodes", 0),
                    "tenant_growth_percent": overview.get("summary", {}).get("tenant_growth_percent", 0),
                    "user_growth_percent": overview.get("summary", {}).get("user_growth_percent", 0),
                    "node_growth_percent": overview.get("summary", {}).get("node_growth_percent", 0),
                    "total_revenue": overview.get("revenue", {}).get("total_revenue", 0),
                    "fixed_revenue": overview.get("revenue", {}).get("fixed_revenue", 0),
                    "node_overage_revenue": overview.get("revenue", {}).get("node_overage_revenue", 0),
                    "llm_overage_revenue": overview.get("revenue", {}).get("llm_overage_revenue", 0),
                    "estimated_margin_percent": overview.get("revenue", {}).get("estimated_margin_percent"),
                    "total_executions": overview.get("usage", {}).get("total_executions", 0),
                    "total_tickets": overview.get("usage", {}).get("total_tickets", 0),
                    "total_llm_tokens": overview.get("usage", {}).get("total_llm_tokens", 0),
                    "total_api_calls": overview.get("usage", {}).get("total_api_calls", 0),
                    "plan_distribution": json.dumps(overview.get("plan_distribution", {})),
                }
            )
            self.db.commit()
            logger.info(f"Created daily platform snapshot for {snapshot_date}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating platform daily snapshot: {e}", exc_info=True)
            raise
