"""
License service for feature-based access control
Checks if tenant has access to specific features based on their subscription plan
"""
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.core.logging import get_logger

logger = get_logger(__name__)


class LicenseService:
    """Service for checking license-based feature access"""
    
    # Feature definitions
    FEATURES = {
        # RBAC Features
        "rbac_basic": "Basic RBAC (predefined roles only)",
        "rbac_custom_roles": "Custom role creation",
        "rbac_permissions": "Granular permission management",
        
        # Integration Features
        "servicenow": "ServiceNow integration",
        "zoho": "Zoho integration",
        "manageengine": "ManageEngine integration",
        "solarwinds": "SolarWinds monitoring integration",
        "datadog": "Datadog monitoring integration",
        "prometheus": "Prometheus monitoring integration",
        "azure_monitor": "Azure Monitor integration",
        "splunk": "Splunk integration",
        
        # Advanced Features
        "advanced_analytics": "Advanced analytics and reporting",
        "api_access": "API access",
        "webhook_access": "Webhook endpoints",
        "bulk_operations": "Bulk user/operation management",
        "activity_logging": "Detailed activity logging",
        "two_factor_auth": "Two-factor authentication",
        
        # Enterprise Features
        "white_labeling": "White-labeling customization",
        "on_premise": "On-premise deployment option",
        "priority_support": "Priority support",
        "sla_guarantees": "SLA guarantees",
        "custom_integrations": "Custom integration development",
    }
    
    @staticmethod
    def has_feature(
        db: Session,
        tenant_id: int,
        feature_name: str
    ) -> bool:
        """
        Check if tenant has access to a specific feature
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            feature_name: Feature name to check
        
        Returns:
            True if tenant has access, False otherwise
        """
        # Get tenant's subscription
        subscription = db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active"
        ).first()
        
        if not subscription:
            # No subscription = no features (or default to free tier)
            return False
        
        # Check if subscription is active
        if not subscription.is_active:
            return False
        
        # If subscription has a license plan, check plan features
        if subscription.license_plan_id:
            plan = db.query(LicensePlan).filter(
                LicensePlan.id == subscription.license_plan_id,
                LicensePlan.is_active == True
            ).first()
            
            if plan:
                return plan.has_feature(feature_name)
        
        # Fallback: If no plan assigned, check if enforcement is disabled
        # (allows custom subscriptions without plans)
        if not subscription.is_enforced:
            logger.warning(f"Tenant {tenant_id} has subscription without license plan - allowing all features")
            return True
        
        # Default: No plan = no features
        return False
    
    @staticmethod
    def get_available_features(db: Session, tenant_id: int) -> Set[str]:
        """
        Get all available features for a tenant
        
        Returns:
            Set of feature names
        """
        subscription = db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active"
        ).first()
        
        if not subscription or not subscription.is_active:
            return set()
        
        if subscription.license_plan_id:
            plan = db.query(LicensePlan).filter(
                LicensePlan.id == subscription.license_plan_id,
                LicensePlan.is_active == True
            ).first()
            
            if plan and plan.features:
                # Return all features that are enabled
                return {feature for feature, enabled in plan.features.items() if enabled}
        
        return set()
    
    @staticmethod
    def get_license_plan(db: Session, tenant_id: int) -> Optional[LicensePlan]:
        """Get the license plan for a tenant"""
        subscription = db.query(TenantSubscription).filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active"
        ).first()
        
        if not subscription or not subscription.license_plan_id:
            return None
        
        return db.query(LicensePlan).filter(
            LicensePlan.id == subscription.license_plan_id
        ).first()
    
    @staticmethod
    def initialize_default_plans(db: Session) -> None:
        """
        Initialize default license plans
        Should be called during system setup
        """
        default_plans = [
            {
                "plan_key": "free",
                "plan_name": "Free",
                "description": "Free tier with basic features",
                "default_max_seats": 3,
                "default_max_nodes": 5,
                "default_monthly_price": "0",
                "features": {
                    "servicenow": True,
                    "rbac_basic": False,  # Legacy roles only
                    "api_access": False,
                    "webhook_access": False,
                },
                "display_order": 1
            },
            {
                "plan_key": "starter",
                "plan_name": "Starter",
                "description": "Starter plan for small teams",
                "default_max_seats": 10,
                "default_max_nodes": 20,
                "default_monthly_price": "99",
                "features": {
                    "servicenow": True,
                    "zoho": True,
                    "manageengine": True,
                    "datadog": True,
                    "prometheus": True,
                    "rbac_basic": True,
                    "api_access": True,
                    "webhook_access": True,
                },
                "display_order": 2
            },
            {
                "plan_key": "professional",
                "plan_name": "Professional",
                "description": "Professional plan for growing teams",
                "default_max_seats": 50,
                "default_max_nodes": 100,
                "default_monthly_price": "299",
                "features": {
                    "servicenow": True,
                    "zoho": True,
                    "manageengine": True,
                    "solarwinds": True,
                    "datadog": True,
                    "prometheus": True,
                    "azure_monitor": True,
                    "splunk": True,
                    "rbac_basic": True,
                    "rbac_custom_roles": True,
                    "rbac_permissions": True,
                    "advanced_analytics": True,
                    "api_access": True,
                    "webhook_access": True,
                    "bulk_operations": True,
                    "activity_logging": True,
                    "priority_support": True,
                },
                "display_order": 3
            },
            {
                "plan_key": "enterprise",
                "plan_name": "Enterprise",
                "description": "Enterprise plan with all features",
                "default_max_seats": 999999,  # Unlimited
                "default_max_nodes": 999999,  # Unlimited
                "default_monthly_price": "custom",
                "features": {
                    # All features enabled
                    "servicenow": True,
                    "zoho": True,
                    "manageengine": True,
                    "solarwinds": True,
                    "datadog": True,
                    "prometheus": True,
                    "azure_monitor": True,
                    "splunk": True,
                    "rbac_basic": True,
                    "rbac_custom_roles": True,
                    "rbac_permissions": True,
                    "advanced_analytics": True,
                    "api_access": True,
                    "webhook_access": True,
                    "bulk_operations": True,
                    "activity_logging": True,
                    "two_factor_auth": True,
                    "white_labeling": True,
                    "on_premise": True,
                    "priority_support": True,
                    "sla_guarantees": True,
                    "custom_integrations": True,
                },
                "display_order": 4
            }
        ]
        
        for plan_data in default_plans:
            existing = db.query(LicensePlan).filter(
                LicensePlan.plan_key == plan_data["plan_key"]
            ).first()
            
            if not existing:
                plan = LicensePlan(
                    plan_key=plan_data["plan_key"],
                    plan_name=plan_data["plan_name"],
                    description=plan_data["description"],
                    default_max_seats=plan_data["default_max_seats"],
                    default_max_nodes=plan_data["default_max_nodes"],
                    default_monthly_price=plan_data["default_monthly_price"],
                    features=plan_data["features"],
                    is_active=True,
                    is_system_plan=True,
                    is_custom=False,
                    display_order=plan_data["display_order"]
                )
                db.add(plan)
        
        db.commit()
        logger.info(f"Initialized {len(default_plans)} default license plans")


# Global instance
license_service = LicenseService()




