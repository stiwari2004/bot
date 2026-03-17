"""
Client Admin — billing, node management, and dashboard endpoints
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_billing_config import TenantBillingConfig
from app.models.tenant_subscription import TenantSubscription
from app.models.credential import InfrastructureConnection
from app.core.logging import get_logger
from app.api.v1.endpoints.client_admin_users import get_current_tenant_admin, DashboardStats

router = APIRouter()
logger = get_logger(__name__)


class BillingViewResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    billing_config: Optional[dict] = None
    subscription: Optional[dict] = None
    current_usage: Optional[dict] = None


class NodeResponse(BaseModel):
    id: int
    name: str
    connection_type: str
    target_host: Optional[str] = None
    environment: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _node_dict(n: InfrastructureConnection) -> dict:
    return {
        "id": n.id, "name": n.name, "connection_type": n.connection_type,
        "target_host": n.target_host, "environment": n.environment,
        "is_active": n.is_active, "created_at": n.created_at,
    }


@router.get("/billing", response_model=BillingViewResponse)
async def get_tenant_billing(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get billing information for the tenant (read-only)"""
    tenant = db.query(Tenant).filter(Tenant.id == current_admin.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    billing_config = db.query(TenantBillingConfig).filter(
        TenantBillingConfig.tenant_id == current_admin.tenant_id
    ).first()
    subscription = db.query(TenantSubscription).filter(
        TenantSubscription.tenant_id == current_admin.tenant_id
    ).first()

    current_usage = {}
    if subscription:
        current_usage = {
            "seats_used": subscription.current_seats,
            "seats_limit": subscription.max_seats,
            "nodes_used": subscription.current_nodes,
            "nodes_limit": subscription.max_nodes,
        }

    billing_data = None
    if billing_config:
        billing_data = {
            "fixed_monthly_cost": float(billing_config.fixed_monthly_cost) if billing_config.fixed_monthly_cost else 0.0,
            "per_node_enabled": billing_config.per_node_enabled,
            "per_node_cost": float(billing_config.per_node_cost) if billing_config.per_node_cost else 0.0,
            "billing_cycle": billing_config.billing_cycle,
            "is_active": billing_config.is_active,
        }

    sub_data = None
    if subscription:
        sub_data = {
            "subscription_name": subscription.subscription_name,
            "max_seats": subscription.max_seats,
            "max_nodes": subscription.max_nodes,
            "monthly_price": float(subscription.monthly_price) if subscription.monthly_price else 0.0,
            "status": subscription.status,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }

    return BillingViewResponse(
        tenant_id=tenant.id, tenant_name=tenant.name,
        billing_config=billing_data, subscription=sub_data, current_usage=current_usage
    )


@router.get("/nodes", response_model=List[NodeResponse])
async def list_tenant_nodes(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """List all infrastructure connections (nodes) for the tenant"""
    query = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    )
    if is_active is not None:
        query = query.filter(InfrastructureConnection.is_active == is_active)
    return [_node_dict(n) for n in query.all()]


@router.put("/nodes/{node_id}/activate")
async def activate_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Activate a node (approve for billing and execution)"""
    node = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.id == node_id,
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_active = True
    db.commit()
    return {"message": "Node activated successfully", "node": _node_dict(node)}


@router.put("/nodes/{node_id}/deactivate")
async def deactivate_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Deactivate a node (remove from billing and execution)"""
    node = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.id == node_id,
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_active = False
    db.commit()
    return {"message": "Node deactivated successfully", "node": _node_dict(node)}


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Get dashboard statistics for the tenant"""
    total_users = db.query(User).filter(User.tenant_id == current_admin.tenant_id).count()
    active_users = db.query(User).filter(
        User.tenant_id == current_admin.tenant_id, User.is_active == True
    ).count()
    total_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id
    ).count()
    active_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id,
        InfrastructureConnection.is_active == True
    ).count()
    pending_nodes = db.query(InfrastructureConnection).filter(
        InfrastructureConnection.tenant_id == current_admin.tenant_id,
        InfrastructureConnection.is_active == False
    ).count()
    return DashboardStats(
        total_users=total_users, active_users=active_users,
        total_nodes=total_nodes, active_nodes=active_nodes, pending_nodes=pending_nodes
    )
