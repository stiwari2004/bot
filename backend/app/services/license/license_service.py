"""
License service for token-based activation and validation.
Provides activate(token), validate(tenant_id), and check_node_limit(tenant_id).
Used by worker registration and session create for enforcement.
"""
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.tenant_subscription import TenantSubscription
from app.models.tenant import Tenant
from app.services.subscription.subscription_tracker import SubscriptionTracker
from app.core.logging import get_logger

logger = get_logger(__name__)


class LicenseService:
    """Token-based license activation and validation for SaaS/PaaS."""

    def __init__(self, db: Session):
        self.db = db
        self.tracker = SubscriptionTracker(db)

    def activate(self, token: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate activation token (license_key) and return tenant info.

        Args:
            token: Activation token (same as license_key in tenant_subscriptions)

        Returns:
            (success, error_message, activation_info)
            activation_info: {tenant_id, tenant_name, is_active, max_nodes, max_seats, ...}
        """
        if not token or not str(token).strip():
            return (False, "Activation token is required", None)

        token = str(token).strip()
        subscription = self.db.query(TenantSubscription).filter(
            TenantSubscription.license_key == token,
        ).first()

        if not subscription:
            return (False, "Invalid activation token", None)

        tenant = self.db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
        if not tenant:
            return (False, "Tenant not found for subscription", None)

        if not tenant.is_active:
            return (False, "Tenant is not active", None)

        if subscription.status != "active":
            return (False, f"Subscription is not active (status={subscription.status})", None)

        if subscription.expires_at and datetime.now(timezone.utc) >= subscription.expires_at:
            return (False, "Subscription has expired", None)

        self.tracker.update_usage(subscription.tenant_id)

        return (True, None, {
            "tenant_id": subscription.tenant_id,
            "tenant_name": tenant.name,
            "is_active": subscription.is_active,
            "max_nodes": subscription.max_nodes,
            "max_seats": subscription.max_seats,
            "current_nodes": subscription.current_nodes,
            "current_seats": subscription.current_seats,
        })

    def validate(self, tenant_id: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Re-validate license for a tenant (e.g. for heartbeat).

        Returns:
            (is_valid, error_message, validation_info)
        """
        subscription = self.tracker.get_subscription(tenant_id)
        if not subscription:
            return (True, None, {"has_subscription": False, "unlimited": True})

        if not subscription.is_active:
            return (False, f"Subscription is not active (status={subscription.status})", None)

        self.tracker.update_usage(tenant_id)

        return (True, None, {
            "tenant_id": tenant_id,
            "is_active": subscription.is_active,
            "max_nodes": subscription.max_nodes,
            "current_nodes": subscription.current_nodes,
            "nodes_remaining": subscription.nodes_remaining,
        })

    def check_node_limit(self, tenant_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can add another node.

        Returns:
            (allowed, error_message)
        """
        return self.tracker.check_node_limit(tenant_id)
