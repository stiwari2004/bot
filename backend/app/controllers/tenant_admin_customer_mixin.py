"""
Mixin: MSP customer tenant CRUD operations
"""
from decimal import Decimal
from typing import Dict, Any, List

from fastapi import HTTPException
from sqlalchemy import func

from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.models.tenant_billing_config import TenantBillingConfig
from app.services.auth import get_password_hash

logger = get_logger(__name__)


class TenantAdminCustomerMixin:
    """Customer CRUD for TenantAdminController."""

    def list_customers(self) -> List[dict]:
        customers = self.tenant_repo.get_customers_for_msp(self.msp_tenant_id)
        return [self._format_customer(t) for t in customers]

    def create_customer(self, customer_data, msp_tenant: Tenant) -> dict:
        db = self.db
        if not msp_tenant.is_msp:
            raise HTTPException(status_code=403, detail="Your tenant is not an MSP")

        existing = db.query(Tenant).filter(Tenant.name == customer_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant with name '{customer_data.name}' already exists")

        if customer_data.subdomain_slug:
            existing_slug = db.query(Tenant).filter(Tenant.subdomain_slug == customer_data.subdomain_slug).first()
            if existing_slug:
                raise HTTPException(
                    status_code=400, detail=f"Tenant with subdomain '{customer_data.subdomain_slug}' already exists"
                )

        existing_user = db.query(User).filter(
            func.lower(User.email) == func.lower(customer_data.admin_email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail=f"User with email '{customer_data.admin_email}' already exists")

        customer_tenant = Tenant(
            name=customer_data.name,
            subdomain_slug=customer_data.subdomain_slug,
            description=customer_data.description,
            deployment_type="saas",
            platform_managed=True,
            contact_email=customer_data.contact_email,
            contact_name=customer_data.contact_name,
            contact_phone=customer_data.contact_phone,
            onboarding_status="pending",
            is_active=True,
            is_msp=False,
            parent_tenant_id=msp_tenant.id,
        )
        db.add(customer_tenant)
        db.flush()

        from app.services.subscription.subscription_tracker import SubscriptionTracker
        tracker = SubscriptionTracker(db)
        allowed, error_msg = tracker.check_seat_limit(customer_tenant.id)
        if not allowed:
            db.rollback()
            raise HTTPException(status_code=403, detail=error_msg or "Seat limit reached for customer tenant")

        admin_user = User(
            tenant_id=customer_tenant.id,
            email=customer_data.admin_email,
            password_hash=get_password_hash(customer_data.admin_password),
            full_name=customer_data.admin_full_name or customer_data.contact_name,
            role="tenant_admin",
            is_active=True,
        )
        db.add(admin_user)

        if customer_data.billing_config:
            bc = customer_data.billing_config
            db.add(TenantBillingConfig(
                tenant_id=customer_tenant.id,
                fixed_monthly_cost=Decimal(str(bc.get("fixed_monthly_cost", 0))),
                per_node_enabled=bc.get("per_node_enabled", False),
                per_node_cost=Decimal(str(bc.get("per_node_cost", 0))),
                node_count_override=bc.get("node_count_override"),
                per_ticket_received_enabled=bc.get("per_ticket_received_enabled", False),
                per_ticket_received_cost=Decimal(str(bc.get("per_ticket_received_cost", 0))),
                per_ticket_resolved_enabled=bc.get("per_ticket_resolved_enabled", False),
                per_ticket_resolved_cost=Decimal(str(bc.get("per_ticket_resolved_cost", 0))),
                per_execution_enabled=bc.get("per_execution_enabled", False),
                per_execution_cost=Decimal(str(bc.get("per_execution_cost", 0))),
                per_api_call_enabled=bc.get("per_api_call_enabled", False),
                per_api_call_cost=Decimal(str(bc.get("per_api_call_cost", 0))),
                per_llm_token_enabled=bc.get("per_llm_token_enabled", False),
                per_llm_token_cost=Decimal(str(bc.get("per_llm_token_cost", 0))),
                billing_cycle=bc.get("billing_cycle", "monthly"),
                billing_day=bc.get("billing_day", 1),
                is_active=bc.get("is_active", True),
            ))

        if customer_data.subscription_config:
            from app.models.tenant_subscription import TenantSubscription
            sc = customer_data.subscription_config
            db.add(TenantSubscription(
                tenant_id=customer_tenant.id,
                max_seats=sc.get("max_seats", 5),
                max_nodes=sc.get("max_nodes", 20),
                subscription_name=sc.get("subscription_name"),
                monthly_price=Decimal(str(sc.get("monthly_price", 0))),
                seat_overage_rate=Decimal(str(sc.get("seat_overage_rate", 0))),
                node_overage_rate=Decimal(str(sc.get("node_overage_rate", 0))),
                is_enforced=sc.get("is_enforced", True),
                expires_at=None,
                auto_renew=sc.get("auto_renew", True),
                notes=sc.get("notes"),
                created_by=None,
                status="active",
            ))

        db.commit()
        db.refresh(customer_tenant)

        if customer_data.subscription_config:
            SubscriptionTracker(db).update_usage(customer_tenant.id)

        logger.info(f"Tenant admin {self.admin_email} created customer {customer_tenant.name} (id={customer_tenant.id})")
        return self._format_customer(customer_tenant)

    def get_customer(self, customer_id: int) -> dict:
        self._check_access(customer_id)
        customer = self.tenant_repo.get_customer_by_id(customer_id, self.msp_tenant_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return self._format_customer(customer)

    def update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> dict:
        db = self.db
        self._check_access(customer_id)
        customer = db.query(Tenant).filter(
            Tenant.id == customer_id, Tenant.parent_tenant_id == self.msp_tenant_id,
        ).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if "name" in customer_data:
            existing = db.query(Tenant).filter(
                Tenant.name == customer_data["name"], Tenant.id != customer_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Tenant with name '{customer_data['name']}' already exists")
            customer.name = customer_data["name"]

        if "subdomain_slug" in customer_data:
            if customer_data["subdomain_slug"]:
                existing = db.query(Tenant).filter(
                    Tenant.subdomain_slug == customer_data["subdomain_slug"], Tenant.id != customer_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400, detail=f"Tenant with subdomain '{customer_data['subdomain_slug']}' already exists"
                    )
            customer.subdomain_slug = customer_data.get("subdomain_slug")

        for field in ("description", "contact_email", "contact_name", "contact_phone", "is_active", "onboarding_status"):
            if field in customer_data:
                setattr(customer, field, customer_data[field])

        db.commit()
        db.refresh(customer)
        logger.info(f"MSP admin {self.admin_email} updated customer {customer.name} (id={customer.id})")
        return self._format_customer(customer)

    def delete_customer(self, customer_id: int) -> dict:
        db = self.db
        self._check_access(customer_id)
        customer = db.query(Tenant).filter(
            Tenant.id == customer_id, Tenant.parent_tenant_id == self.msp_tenant_id,
        ).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.is_active = False
        db.commit()
        logger.info(f"MSP admin {self.admin_email} deactivated customer {customer.name} (id={customer.id})")
        return {"message": f"Customer {customer_id} deactivated successfully"}
