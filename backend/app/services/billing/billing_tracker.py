"""
Billing tracker service - tracks usage metrics for billing
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession
from app.models.credential import InfrastructureConnection
from app.models.tenant_billing_config import TenantBillingUsage
from app.models.credential import InfrastructureConnection

logger = get_logger(__name__)


class BillingTracker:
    """Track usage metrics for billing calculation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def track_ticket_received(self, tenant_id: int, ticket_id: int) -> None:
        """Track when a ticket is received/created"""
        try:
            # Get or create usage record for current period
            usage = self._get_or_create_current_period_usage(tenant_id)
            usage.tickets_received += 1
            self.db.commit()
            logger.debug(f"Tracked ticket received: tenant={tenant_id}, ticket={ticket_id}")
        except Exception as e:
            logger.error(f"Error tracking ticket received: {e}", exc_info=True)
            self.db.rollback()
    
    def track_ticket_resolved(self, tenant_id: int, ticket_id: int) -> None:
        """Track when a ticket is resolved"""
        try:
            # Get or create usage record for current period
            usage = self._get_or_create_current_period_usage(tenant_id)
            usage.tickets_resolved += 1
            self.db.commit()
            logger.debug(f"Tracked ticket resolved: tenant={tenant_id}, ticket={ticket_id}")
        except Exception as e:
            logger.error(f"Error tracking ticket resolved: {e}", exc_info=True)
            self.db.rollback()
    
    def track_execution_session(self, tenant_id: int, session_id: int) -> None:
        """Track when an execution session is created"""
        try:
            usage = self._get_or_create_current_period_usage(tenant_id)
            usage.execution_sessions += 1
            self.db.commit()
            logger.debug(f"Tracked execution session: tenant={tenant_id}, session={session_id}")
        except Exception as e:
            logger.error(f"Error tracking execution session: {e}", exc_info=True)
            self.db.rollback()
    
    def track_api_call(self, tenant_id: int, endpoint: str) -> None:
        """Track API call"""
        try:
            usage = self._get_or_create_current_period_usage(tenant_id)
            usage.api_calls += 1
            self.db.commit()
            logger.debug(f"Tracked API call: tenant={tenant_id}, endpoint={endpoint}")
        except Exception as e:
            logger.error(f"Error tracking API call: {e}", exc_info=True)
            self.db.rollback()
    
    def track_llm_tokens(self, tenant_id: int, tokens: int) -> None:
        """Track LLM tokens consumed (tokens should be in thousands)"""
        try:
            usage = self._get_or_create_current_period_usage(tenant_id)
            usage.llm_tokens += tokens  # Assuming tokens already in thousands
            self.db.commit()
            logger.debug(f"Tracked LLM tokens: tenant={tenant_id}, tokens={tokens}K")
        except Exception as e:
            logger.error(f"Error tracking LLM tokens: {e}", exc_info=True)
            self.db.rollback()
    
    def _get_or_create_current_period_usage(self, tenant_id: int) -> TenantBillingUsage:
        """Get or create usage record for current billing period"""
        now = datetime.now(timezone.utc)
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        # Calculate period end (last day of current month)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        # Try to get existing usage record
        usage = self.db.query(TenantBillingUsage).filter(
            and_(
                TenantBillingUsage.tenant_id == tenant_id,
                TenantBillingUsage.period_start == period_start,
                TenantBillingUsage.period_end == period_end
            )
        ).first()
        
        if not usage:
            # Create new usage record
            usage = TenantBillingUsage(
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                status="pending"
            )
            self.db.add(usage)
            self.db.flush()
        
        return usage
    
    def get_current_period_usage(self, tenant_id: int) -> Optional[TenantBillingUsage]:
        """Get current period usage record"""
        now = datetime.now(timezone.utc)
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        return self.db.query(TenantBillingUsage).filter(
            and_(
                TenantBillingUsage.tenant_id == tenant_id,
                TenantBillingUsage.period_start == period_start,
                TenantBillingUsage.period_end == period_end
            )
        ).first()
    
    def _get_usage_for_period(
        self,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[TenantBillingUsage]:
        """Get usage record for specific period"""
        return self.db.query(TenantBillingUsage).filter(
            and_(
                TenantBillingUsage.tenant_id == tenant_id,
                TenantBillingUsage.period_start == period_start,
                TenantBillingUsage.period_end == period_end
            )
        ).first()
    
    def count_active_nodes(self, tenant_id: int) -> int:
        """Count active infrastructure connections (nodes) for tenant"""
        return self.db.query(InfrastructureConnection).filter(
            and_(
                InfrastructureConnection.tenant_id == tenant_id,
                InfrastructureConnection.is_active == True
            )
        ).count()

