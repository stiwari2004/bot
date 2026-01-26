"""
Usage Aggregator for dashboard usage metrics
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.credential import InfrastructureConnection
from app.models.tenant_billing_config import TenantBillingUsage
from app.core.logging import get_logger

logger = get_logger(__name__)


class UsageAggregator:
    """Aggregate usage metrics for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_current_month_usage(self) -> dict:
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
