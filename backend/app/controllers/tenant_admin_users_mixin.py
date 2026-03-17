"""
Mixin: MSP customer user CRUD, subscriptions, and dashboard
"""
from decimal import Decimal
from typing import Dict, Any, List

from fastapi import HTTPException
from sqlalchemy import func

from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_password_hash

logger = get_logger(__name__)


class TenantAdminUsersMixin:
    """User CRUD, subscriptions, and dashboard for TenantAdminController."""

    def list_customer_users(self, customer_id: int) -> List[dict]:
        self._check_access(customer_id)
        users = self.user_repo.list_for_tenant(customer_id)
        return [
            {
                "id": u.id, "email": u.email, "full_name": u.full_name,
                "role": u.role, "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]

    def create_customer_user(self, customer_id: int, user_data: Dict[str, Any]) -> dict:
        db = self.db
        self._check_access(customer_id)

        customer_tenant = db.query(Tenant).filter(Tenant.id == customer_id).first()
        if not customer_tenant:
            raise HTTPException(status_code=404, detail=f"Customer tenant {customer_id} not found")
        if customer_tenant.id == self.msp_tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot create users under MSP tenant. Please select a customer (sub-tenant) to create users for.",
            )
        if customer_tenant.is_msp:
            raise HTTPException(
                status_code=403,
                detail="Cannot create users under another MSP tenant. Please select a customer (sub-tenant).",
            )

        existing = db.query(User).filter(func.lower(User.email) == func.lower(user_data["email"])).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"User with email '{user_data['email']}' already exists")

        from app.services.subscription.subscription_tracker import SubscriptionTracker
        allowed, error_msg = SubscriptionTracker(db).check_seat_limit(customer_id)
        if not allowed:
            raise HTTPException(status_code=403, detail=error_msg or "Seat limit reached")

        requested_role = user_data.get("role", "user")
        final_role = "tenant_admin" if requested_role == "admin" else requested_role

        user = User(
            tenant_id=customer_id,
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
            full_name=user_data.get("full_name"),
            role=final_role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        self._sync_user_billing(customer_id, user)

        logger.info(f"MSP admin {self.admin_email} created user {user.email} for customer {customer_id}")
        return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "is_active": user.is_active}

    def update_customer_user(self, customer_id: int, user_id: int, user_data: Dict[str, Any]) -> dict:
        db = self.db
        self._check_access(customer_id)

        user = db.query(User).filter(User.id == user_id, User.tenant_id == customer_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found for customer {customer_id}")

        if "role" in user_data:
            if user_data["role"] not in ("admin", "user", "viewer"):
                raise HTTPException(status_code=400, detail="role must be 'admin', 'user', or 'viewer'")
            user.role = "tenant_admin" if user_data["role"] == "admin" else user_data["role"]
        if "full_name" in user_data:
            user.full_name = user_data["full_name"]
        if "is_active" in user_data:
            user.is_active = user_data["is_active"]
        if "password" in user_data and user_data["password"]:
            user.password_hash = get_password_hash(user_data["password"])

        db.commit()
        db.refresh(user)
        self._sync_user_billing(customer_id, user)

        logger.info(f"MSP admin {self.admin_email} updated user {user.email} for customer {customer_id}")
        return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "is_active": user.is_active}

    def delete_customer_user(self, customer_id: int, user_id: int) -> dict:
        db = self.db
        self._check_access(customer_id)
        user = db.query(User).filter(User.id == user_id, User.tenant_id == customer_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found for customer {customer_id}")
        user.is_active = False
        db.commit()
        logger.info(f"MSP admin {self.admin_email} deactivated user {user.email} for customer {customer_id}")
        return {"message": f"User {user_id} deactivated successfully"}

    # ── Subscriptions ─────────────────────────────────────────────────────

    def get_customer_subscription(self, customer_id: int) -> dict:
        self._check_access(customer_id)
        from app.services.subscription.subscription_tracker import SubscriptionTracker

        subscription = self.subscription_repo.get_for_tenant(customer_id)
        if not subscription:
            return {"has_subscription": False}

        SubscriptionTracker(self.db).update_usage(customer_id)
        self.db.refresh(subscription)
        return {
            "id": subscription.id, "max_seats": subscription.max_seats, "max_nodes": subscription.max_nodes,
            "current_seats": subscription.current_seats, "current_nodes": subscription.current_nodes,
            "seats_remaining": subscription.seats_remaining, "nodes_remaining": subscription.nodes_remaining,
            "seats_exceeded": subscription.seats_exceeded, "nodes_exceeded": subscription.nodes_exceeded,
            "subscription_name": subscription.subscription_name, "monthly_price": float(subscription.monthly_price),
            "status": subscription.status, "is_enforced": subscription.is_enforced, "is_active": subscription.is_active,
        }

    def create_customer_subscription(self, customer_id: int, subscription_data: Dict[str, Any]) -> dict:
        db = self.db
        self._check_access(customer_id)
        from app.models.tenant_subscription import TenantSubscription
        from app.services.subscription.subscription_tracker import SubscriptionTracker

        existing = db.query(TenantSubscription).filter(TenantSubscription.tenant_id == customer_id).first()
        if existing:
            existing.max_seats = subscription_data.get("max_seats", existing.max_seats)
            existing.max_nodes = subscription_data.get("max_nodes", existing.max_nodes)
            for field in ("subscription_name", "is_enforced", "auto_renew", "notes"):
                if field in subscription_data:
                    setattr(existing, field, subscription_data[field])
            for decimal_field in ("monthly_price", "seat_overage_rate", "node_overage_rate"):
                if decimal_field in subscription_data:
                    setattr(existing, decimal_field, Decimal(str(subscription_data[decimal_field])))
            db.commit()
            db.refresh(existing)
            SubscriptionTracker(db).update_usage(customer_id)
            db.refresh(existing)
            logger.info(f"MSP admin {self.admin_email} updated subscription for customer {customer_id}")
            return {
                "id": existing.id, "max_seats": existing.max_seats, "max_nodes": existing.max_nodes,
                "current_seats": existing.current_seats, "current_nodes": existing.current_nodes,
                "message": "Subscription updated successfully",
            }

        subscription = TenantSubscription(
            tenant_id=customer_id,
            max_seats=subscription_data.get("max_seats", 5),
            max_nodes=subscription_data.get("max_nodes", 20),
            subscription_name=subscription_data.get("subscription_name"),
            monthly_price=Decimal(str(subscription_data.get("monthly_price", 0))),
            seat_overage_rate=Decimal(str(subscription_data.get("seat_overage_rate", 0))),
            node_overage_rate=Decimal(str(subscription_data.get("node_overage_rate", 0))),
            is_enforced=subscription_data.get("is_enforced", True),
            expires_at=None,
            auto_renew=subscription_data.get("auto_renew", True),
            notes=subscription_data.get("notes"),
            created_by=None,
            status="active",
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        SubscriptionTracker(db).update_usage(customer_id)
        db.refresh(subscription)
        logger.info(f"MSP admin {self.admin_email} created subscription for customer {customer_id}")
        return {
            "id": subscription.id, "max_seats": subscription.max_seats, "max_nodes": subscription.max_nodes,
            "current_seats": subscription.current_seats, "current_nodes": subscription.current_nodes,
            "message": "Subscription created successfully",
        }

    # ── Dashboard ─────────────────────────────────────────────────────────

    def get_msp_dashboard(self, current_user) -> dict:
        db = self.db
        msp_tenant_id = self.msp_tenant_id
        from app.services.tenant_admin_auth import get_allowed_tenant_ids_for_msp

        customer_count = db.query(Tenant).filter(
            Tenant.parent_tenant_id == msp_tenant_id,
            Tenant.is_msp == False,
            Tenant.is_active == True,
        ).count()

        allowed_tenant_ids = get_allowed_tenant_ids_for_msp(msp_tenant_id, db)
        total_users = db.query(User).filter(
            User.tenant_id.in_(allowed_tenant_ids), User.is_active == True
        ).count()

        from app.models.credential import InfrastructureConnection
        total_nodes = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id.in_(allowed_tenant_ids),
            InfrastructureConnection.is_active == True,
        ).count()

        from app.models.tenant_subscription import TenantSubscription
        subscriptions = db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id.in_(allowed_tenant_ids),
            TenantSubscription.status == "active",
        ).all()

        return {
            "msp_tenant": {"id": current_user.tenant.id, "name": current_user.tenant.name},
            "customers": {"total": customer_count, "active": customer_count},
            "users": {
                "total": total_users,
                "seats_used": sum(s.current_seats for s in subscriptions),
                "seats_limit": sum(s.max_seats for s in subscriptions),
            },
            "nodes": {
                "total": total_nodes,
                "nodes_used": sum(s.current_nodes for s in subscriptions),
                "nodes_limit": sum(s.max_nodes for s in subscriptions),
            },
            "subscriptions": {"total": len(subscriptions), "active": len([s for s in subscriptions if s.is_active])},
        }

    # ── Private helper ────────────────────────────────────────────────────

    def _sync_user_billing(self, tenant_id: int, user) -> None:
        try:
            from app.services.central_client import sync_users_for_billing
            sync_users_for_billing(tenant_id, [{
                "id": user.id, "email": user.email, "full_name": user.full_name,
                "role": user.role, "tenant_id": user.tenant_id, "node_details": None,
            }])
        except Exception as e:
            logger.warning("PaaS sync_users_for_billing failed: %s", e)
