"""
Billing calculator service - calculates monthly bills based on usage and config
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.tenant_billing_config import TenantBillingConfig, TenantBillingUsage
from app.services.billing.billing_tracker import BillingTracker

logger = get_logger(__name__)


class BillingCalculator:
    """Calculate billing based on configuration and usage"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracker = BillingTracker(db)
    
    def calculate_monthly_bill(
        self,
        tenant_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict:
        """
        Calculate monthly bill for tenant
        
        Returns:
        {
            "fixed_cost": Decimal,
            "node_cost": Decimal,
            "node_count": int,
            "ticket_received_cost": Decimal,
            "ticket_resolved_cost": Decimal,
            "execution_cost": Decimal,
            "api_call_cost": Decimal,
            "llm_token_cost": Decimal,
            "total_cost": Decimal,
            "usage": {...},
            "breakdown": {...}
        }
        """
        # Get billing config
        config = self.db.query(TenantBillingConfig).filter(
            TenantBillingConfig.tenant_id == tenant_id,
            TenantBillingConfig.is_active == True
        ).first()
        
        if not config:
            logger.warning(f"No billing config found for tenant {tenant_id}, using defaults")
            return self._calculate_with_defaults(tenant_id, period_start, period_end)
        
        # Get usage for period
        if period_start and period_end:
            usage = self.tracker._get_usage_for_period(tenant_id, period_start, period_end)
        else:
            usage = self.tracker.get_current_period_usage(tenant_id)
        
        if not usage:
            # Create empty usage record
            usage = self.tracker._get_or_create_current_period_usage(tenant_id)
        
        # Calculate costs
        fixed_cost = Decimal(str(config.fixed_monthly_cost))
        
        # Node cost
        node_cost = Decimal(0)
        node_count = 0
        if config.per_node_enabled:
            if config.node_count_override is not None:
                node_count = config.node_count_override
            else:
                node_count = self.tracker.count_active_nodes(tenant_id)
            node_cost = Decimal(str(config.per_node_cost)) * node_count
        
        # Ticket received cost
        ticket_received_cost = Decimal(0)
        if config.per_ticket_received_enabled:
            ticket_received_cost = Decimal(str(config.per_ticket_received_cost)) * usage.tickets_received
        
        # Ticket resolved cost
        ticket_resolved_cost = Decimal(0)
        if config.per_ticket_resolved_enabled:
            ticket_resolved_cost = Decimal(str(config.per_ticket_resolved_cost)) * usage.tickets_resolved
        
        # Execution cost
        execution_cost = Decimal(0)
        if config.per_execution_enabled:
            execution_cost = Decimal(str(config.per_execution_cost)) * usage.execution_sessions
        
        # API call cost
        api_call_cost = Decimal(0)
        if config.per_api_call_enabled:
            api_call_cost = Decimal(str(config.per_api_call_cost)) * usage.api_calls
        
        # LLM token cost
        llm_token_cost = Decimal(0)
        if config.per_llm_token_enabled:
            llm_token_cost = Decimal(str(config.per_llm_token_cost)) * usage.llm_tokens
        
        # Total
        total_cost = (
            fixed_cost +
            node_cost +
            ticket_received_cost +
            ticket_resolved_cost +
            execution_cost +
            api_call_cost +
            llm_token_cost
        )
        
        # Update usage record with calculated costs
        usage.fixed_cost = float(fixed_cost)
        usage.node_cost = float(node_cost)
        usage.ticket_received_cost = float(ticket_received_cost)
        usage.ticket_resolved_cost = float(ticket_resolved_cost)
        usage.execution_cost = float(execution_cost)
        usage.api_call_cost = float(api_call_cost)
        usage.llm_token_cost = float(llm_token_cost)
        usage.total_cost = float(total_cost)
        usage.active_nodes = node_count
        usage.status = "calculated"
        
        self.db.commit()
        
        return {
            "fixed_cost": float(fixed_cost),
            "node_cost": float(node_cost),
            "node_count": node_count,
            "ticket_received_cost": float(ticket_received_cost),
            "ticket_resolved_cost": float(ticket_resolved_cost),
            "execution_cost": float(execution_cost),
            "api_call_cost": float(api_call_cost),
            "llm_token_cost": float(llm_token_cost),
            "total_cost": float(total_cost),
            "usage": {
                "tickets_received": usage.tickets_received,
                "tickets_resolved": usage.tickets_resolved,
                "execution_sessions": usage.execution_sessions,
                "api_calls": usage.api_calls,
                "llm_tokens": usage.llm_tokens,
                "active_nodes": node_count
            },
            "breakdown": {
                "fixed": {
                    "enabled": True,
                    "cost": float(fixed_cost),
                    "description": "Fixed monthly base cost"
                },
                "nodes": {
                    "enabled": config.per_node_enabled,
                    "count": node_count,
                    "rate": float(config.per_node_cost),
                    "cost": float(node_cost),
                    "description": f"{node_count} nodes × ₹{config.per_node_cost}/node"
                },
                "tickets_received": {
                    "enabled": config.per_ticket_received_enabled,
                    "count": usage.tickets_received,
                    "rate": float(config.per_ticket_received_cost),
                    "cost": float(ticket_received_cost),
                    "description": f"{usage.tickets_received} tickets received × ₹{config.per_ticket_received_cost}/ticket"
                },
                "tickets_resolved": {
                    "enabled": config.per_ticket_resolved_enabled,
                    "count": usage.tickets_resolved,
                    "rate": float(config.per_ticket_resolved_cost),
                    "cost": float(ticket_resolved_cost),
                    "description": f"{usage.tickets_resolved} tickets resolved × ₹{config.per_ticket_resolved_cost}/ticket"
                },
                "executions": {
                    "enabled": config.per_execution_enabled,
                    "count": usage.execution_sessions,
                    "rate": float(config.per_execution_cost),
                    "cost": float(execution_cost),
                    "description": f"{usage.execution_sessions} executions × ₹{config.per_execution_cost}/execution"
                },
                "api_calls": {
                    "enabled": config.per_api_call_enabled,
                    "count": usage.api_calls,
                    "rate": float(config.per_api_call_cost),
                    "cost": float(api_call_cost),
                    "description": f"{usage.api_calls} API calls × ₹{config.per_api_call_cost}/call"
                },
                "llm_tokens": {
                    "enabled": config.per_llm_token_enabled,
                    "count": usage.llm_tokens,
                    "rate": float(config.per_llm_token_cost),
                    "cost": float(llm_token_cost),
                    "description": f"{usage.llm_tokens}K tokens × ₹{config.per_llm_token_cost}/1K tokens"
                }
            }
        }
    
    def _get_usage_for_period(
        self,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[TenantBillingUsage]:
        """Get usage record for specific period"""
        from app.models.tenant_billing_config import TenantBillingUsage
        return self.db.query(TenantBillingUsage).filter(
            TenantBillingUsage.tenant_id == tenant_id,
            TenantBillingUsage.period_start == period_start,
            TenantBillingUsage.period_end == period_end
        ).first()
    
    def _calculate_with_defaults(
        self,
        tenant_id: int,
        period_start: Optional[datetime],
        period_end: Optional[datetime]
    ) -> Dict:
        """Calculate with default values if no config exists"""
        return {
            "fixed_cost": 0.0,
            "node_cost": 0.0,
            "node_count": 0,
            "ticket_received_cost": 0.0,
            "ticket_resolved_cost": 0.0,
            "execution_cost": 0.0,
            "api_call_cost": 0.0,
            "llm_token_cost": 0.0,
            "total_cost": 0.0,
            "usage": {
                "tickets_received": 0,
                "tickets_resolved": 0,
                "execution_sessions": 0,
                "api_calls": 0,
                "llm_tokens": 0,
                "active_nodes": 0
            },
            "breakdown": {}
        }

