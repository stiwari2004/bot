"""
Subscription tracker service - tracks usage and enforces limits
"""
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.models.credential import InfrastructureConnection

logger = get_logger(__name__)


class SubscriptionTracker:
    """Track subscription usage and enforce limits"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_subscription(self, tenant_id: int) -> Optional[TenantSubscription]:
        """Get active subscription for tenant"""
        return self.db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active"
        ).first()
    
    def update_usage(self, tenant_id: int) -> Tuple[int, int]:
        """
        Update current usage for a tenant's subscription.
        Returns (current_seats, current_nodes)
        """
        subscription = self.get_subscription(tenant_id)
        if not subscription:
            return (0, 0)
        
        # Count active users (seats)
        active_users = self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_active == True
        ).count()
        
        # Count active infrastructure connections (nodes)
        active_nodes = self.db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        ).count()
        
        # Update subscription
        subscription.current_seats = active_users
        subscription.current_nodes = active_nodes
        self.db.commit()
        
        logger.debug(f"Updated subscription usage for tenant {tenant_id}: {active_users} seats, {active_nodes} nodes")
        
        return (active_users, active_nodes)
    
    def check_seat_limit(self, tenant_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can add another seat (user).
        Returns (allowed, error_message)
        """
        subscription = self.get_subscription(tenant_id)
        if not subscription:
            # No subscription = unlimited (for backward compatibility)
            return (True, None)
        
        if not subscription.is_active:
            return (False, "Subscription is not active")
        
        if not subscription.is_enforced:
            # Enforcement disabled = allow
            return (True, None)
        
        # Update usage first
        current_seats, _ = self.update_usage(tenant_id)
        
        if current_seats >= subscription.max_seats:
            return (
                False,
                f"Seat limit reached ({current_seats}/{subscription.max_seats}). Please upgrade your subscription or contact support."
            )
        
        return (True, None)
    
    def check_node_limit(self, tenant_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can add another node (infrastructure connection).
        Returns (allowed, error_message)
        """
        subscription = self.get_subscription(tenant_id)
        if not subscription:
            # No subscription = unlimited
            return (True, None)
        
        if not subscription.is_active:
            return (False, "Subscription is not active")
        
        if not subscription.is_enforced:
            # Enforcement disabled = allow
            return (True, None)
        
        # Update usage first
        _, current_nodes = self.update_usage(tenant_id)
        
        if current_nodes >= subscription.max_nodes:
            return (
                False,
                f"Node limit reached ({current_nodes}/{subscription.max_nodes}). Please upgrade your subscription or contact support."
            )
        
        return (True, None)
    
    def get_usage_summary(self, tenant_id: int) -> Dict:
        """Get usage summary for a tenant"""
        subscription = self.get_subscription(tenant_id)
        if not subscription:
            return {
                "has_subscription": False,
                "unlimited": True
            }
        
        # Update usage
        current_seats, current_nodes = self.update_usage(tenant_id)
        
        return {
            "has_subscription": True,
            "subscription_id": subscription.id,
            "subscription_name": subscription.subscription_name,
            "status": subscription.status,
            "is_active": subscription.is_active,
            "is_enforced": subscription.is_enforced,
            "seats": {
                "current": current_seats,
                "max": subscription.max_seats,
                "remaining": subscription.seats_remaining,
                "exceeded": subscription.seats_exceeded,
                "usage_percent": round((current_seats / subscription.max_seats * 100) if subscription.max_seats > 0 else 0, 2)
            },
            "nodes": {
                "current": current_nodes,
                "max": subscription.max_nodes,
                "remaining": subscription.nodes_remaining,
                "exceeded": subscription.nodes_exceeded,
                "usage_percent": round((current_nodes / subscription.max_nodes * 100) if subscription.max_nodes > 0 else 0, 2)
            },
            "monthly_price": float(subscription.monthly_price),
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }


