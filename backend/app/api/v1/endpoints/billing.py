"""
Billing configuration and management endpoints (Super Admin only)
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from decimal import Decimal

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_billing_config import TenantBillingConfig, TenantBillingUsage
from app.models.user import User
from app.services.auth import get_current_user
from app.services.billing.billing_calculator import BillingCalculator
from app.services.billing.billing_tracker import BillingTracker

router = APIRouter()


# Request/Response Models
class BillingConfigRequest(BaseModel):
    """Request model for billing configuration"""
    fixed_monthly_cost: Decimal = Field(0.00, ge=0, description="Fixed monthly base cost")
    
    # Per-Node
    per_node_enabled: bool = Field(False, description="Enable per-node billing")
    per_node_cost: Decimal = Field(0.00, ge=0, description="Cost per node per month")
    node_count_override: Optional[int] = Field(None, ge=0, description="Manual node count override (null = auto)")
    
    # Ticket Based
    per_ticket_received_enabled: bool = Field(False, description="Enable per-ticket-received billing")
    per_ticket_received_cost: Decimal = Field(0.00, ge=0, description="Cost per ticket received")
    
    per_ticket_resolved_enabled: bool = Field(False, description="Enable per-ticket-resolved billing")
    per_ticket_resolved_cost: Decimal = Field(0.00, ge=0, description="Cost per ticket resolved")
    
    # Execution Based
    per_execution_enabled: bool = Field(False, description="Enable per-execution billing")
    per_execution_cost: Decimal = Field(0.00, ge=0, description="Cost per execution session")
    
    # API Based
    per_api_call_enabled: bool = Field(False, description="Enable per-API-call billing")
    per_api_call_cost: Decimal = Field(0.0000, ge=0, description="Cost per API call")
    
    # LLM Based
    per_llm_token_enabled: bool = Field(False, description="Enable per-LLM-token billing")
    per_llm_token_cost: Decimal = Field(0.000000, ge=0, description="Cost per 1K LLM tokens")
    
    # Billing Period
    billing_cycle: str = Field("monthly", description="Billing cycle: monthly, quarterly, annual")
    billing_day: int = Field(1, ge=1, le=28, description="Day of month to bill")
    
    is_active: bool = Field(True, description="Is billing config active")


class BillingConfigResponse(BaseModel):
    """Response model for billing configuration"""
    id: int
    tenant_id: int
    tenant_name: str
    fixed_monthly_cost: float
    per_node_enabled: bool
    per_node_cost: float
    node_count_override: Optional[int]
    per_ticket_received_enabled: bool
    per_ticket_received_cost: float
    per_ticket_resolved_enabled: bool
    per_ticket_resolved_cost: float
    per_execution_enabled: bool
    per_execution_cost: float
    per_api_call_enabled: bool
    per_api_call_cost: float
    per_llm_token_enabled: bool
    per_llm_token_cost: float
    billing_cycle: str
    billing_day: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class BillingPreviewResponse(BaseModel):
    """Response model for billing preview"""
    tenant_id: int
    tenant_name: str
    period_start: datetime
    period_end: datetime
    fixed_cost: float
    node_cost: float
    node_count: int
    ticket_received_cost: float
    ticket_resolved_cost: float
    execution_cost: float
    api_call_cost: float
    llm_token_cost: float
    total_cost: float
    usage: dict
    breakdown: dict


def require_super_admin(current_user: User = Depends(get_current_user)):
    """Require super admin role"""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


@router.get("/config/{tenant_id}", response_model=BillingConfigResponse)
async def get_billing_config(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get billing configuration for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    config = db.query(TenantBillingConfig).filter(
        TenantBillingConfig.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Return default config
        return BillingConfigResponse(
            id=0,
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            fixed_monthly_cost=0.0,
            per_node_enabled=False,
            per_node_cost=0.0,
            node_count_override=None,
            per_ticket_received_enabled=False,
            per_ticket_received_cost=0.0,
            per_ticket_resolved_enabled=False,
            per_ticket_resolved_cost=0.0,
            per_execution_enabled=False,
            per_execution_cost=0.0,
            per_api_call_enabled=False,
            per_api_call_cost=0.0,
            per_llm_token_enabled=False,
            per_llm_token_cost=0.0,
            billing_cycle="monthly",
            billing_day=1,
            is_active=True,
            created_at=datetime.now(),
            updated_at=None
        )
    
    return BillingConfigResponse(
        id=config.id,
        tenant_id=config.tenant_id,
        tenant_name=tenant.name,
        fixed_monthly_cost=float(config.fixed_monthly_cost),
        per_node_enabled=config.per_node_enabled,
        per_node_cost=float(config.per_node_cost),
        node_count_override=config.node_count_override,
        per_ticket_received_enabled=config.per_ticket_received_enabled,
        per_ticket_received_cost=float(config.per_ticket_received_cost),
        per_ticket_resolved_enabled=config.per_ticket_resolved_enabled,
        per_ticket_resolved_cost=float(config.per_ticket_resolved_cost),
        per_execution_enabled=config.per_execution_enabled,
        per_execution_cost=float(config.per_execution_cost),
        per_api_call_enabled=config.per_api_call_enabled,
        per_api_call_cost=float(config.per_api_call_cost),
        per_llm_token_enabled=config.per_llm_token_enabled,
        per_llm_token_cost=float(config.per_llm_token_cost),
        billing_cycle=config.billing_cycle,
        billing_day=config.billing_day,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.put("/config/{tenant_id}", response_model=BillingConfigResponse)
async def update_billing_config(
    tenant_id: int,
    config_data: BillingConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Create or update billing configuration for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get existing config or create new
    config = db.query(TenantBillingConfig).filter(
        TenantBillingConfig.tenant_id == tenant_id
    ).first()
    
    if not config:
        config = TenantBillingConfig(tenant_id=tenant_id)
        db.add(config)
    
    # Update fields
    config.fixed_monthly_cost = config_data.fixed_monthly_cost
    config.per_node_enabled = config_data.per_node_enabled
    config.per_node_cost = config_data.per_node_cost
    config.node_count_override = config_data.node_count_override
    config.per_ticket_received_enabled = config_data.per_ticket_received_enabled
    config.per_ticket_received_cost = config_data.per_ticket_received_cost
    config.per_ticket_resolved_enabled = config_data.per_ticket_resolved_enabled
    config.per_ticket_resolved_cost = config_data.per_ticket_resolved_cost
    config.per_execution_enabled = config_data.per_execution_enabled
    config.per_execution_cost = config_data.per_execution_cost
    config.per_api_call_enabled = config_data.per_api_call_enabled
    config.per_api_call_cost = config_data.per_api_call_cost
    config.per_llm_token_enabled = config_data.per_llm_token_enabled
    config.per_llm_token_cost = config_data.per_llm_token_cost
    config.billing_cycle = config_data.billing_cycle
    config.billing_day = config_data.billing_day
    config.is_active = config_data.is_active
    
    db.commit()
    db.refresh(config)
    
    return BillingConfigResponse(
        id=config.id,
        tenant_id=config.tenant_id,
        tenant_name=tenant.name,
        fixed_monthly_cost=float(config.fixed_monthly_cost),
        per_node_enabled=config.per_node_enabled,
        per_node_cost=float(config.per_node_cost),
        node_count_override=config.node_count_override,
        per_ticket_received_enabled=config.per_ticket_received_enabled,
        per_ticket_received_cost=float(config.per_ticket_received_cost),
        per_ticket_resolved_enabled=config.per_ticket_resolved_enabled,
        per_ticket_resolved_cost=float(config.per_ticket_resolved_cost),
        per_execution_enabled=config.per_execution_enabled,
        per_execution_cost=float(config.per_execution_cost),
        per_api_call_enabled=config.per_api_call_enabled,
        per_api_call_cost=float(config.per_api_call_cost),
        per_llm_token_enabled=config.per_llm_token_enabled,
        per_llm_token_cost=float(config.per_llm_token_cost),
        billing_cycle=config.billing_cycle,
        billing_day=config.billing_day,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/preview/{tenant_id}", response_model=BillingPreviewResponse)
async def preview_billing(
    tenant_id: int,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Preview billing calculation for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    calculator = BillingCalculator(db)
    
    # Calculate period
    if month and year:
        from datetime import timezone
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        bill = calculator.calculate_monthly_bill(tenant_id, period_start, period_end)
    else:
        bill = calculator.calculate_monthly_bill(tenant_id)
    
    # Get period dates
    usage = calculator.tracker.get_current_period_usage(tenant_id)
    if usage:
        period_start = usage.period_start
        period_end = usage.period_end
    else:
        now = datetime.now()
        period_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1)
        else:
            period_end = datetime(now.year, now.month + 1, 1)
    
    return BillingPreviewResponse(
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        period_start=period_start,
        period_end=period_end,
        **bill
    )


@router.get("/usage/{tenant_id}")
async def get_billing_usage(
    tenant_id: int,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get billing usage for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tracker = BillingTracker(db)
    
    if month and year:
        from datetime import timezone
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        usage = tracker._get_usage_for_period(tenant_id, period_start, period_end)
    else:
        usage = tracker.get_current_period_usage(tenant_id)
    
    if not usage:
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "period_start": None,
            "period_end": None,
            "tickets_received": 0,
            "tickets_resolved": 0,
            "execution_sessions": 0,
            "api_calls": 0,
            "llm_tokens": 0,
            "active_nodes": tracker.count_active_nodes(tenant_id)
        }
    
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "period_start": usage.period_start.isoformat(),
        "period_end": usage.period_end.isoformat(),
        "tickets_received": usage.tickets_received,
        "tickets_resolved": usage.tickets_resolved,
        "execution_sessions": usage.execution_sessions,
        "api_calls": usage.api_calls,
        "llm_tokens": usage.llm_tokens,
        "active_nodes": usage.active_nodes,
        "status": usage.status,
        "total_cost": float(usage.total_cost) if usage.total_cost else 0.0
    }


