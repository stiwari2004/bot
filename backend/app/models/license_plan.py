"""
License Plan model
Defines subscription plans with feature sets
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class LicensePlan(Base):
    """Predefined license plans (Free, Starter, Professional, Enterprise)"""
    __tablename__ = "license_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_key = Column(String(50), unique=True, nullable=False, index=True)  # free, starter, professional, enterprise
    plan_name = Column(String(255), nullable=False)  # Display name
    description = Column(Text, nullable=True)
    
    # Default Limits (can be overridden per subscription)
    default_max_seats = Column(Integer, nullable=False, default=0)
    default_max_nodes = Column(Integer, nullable=False, default=0)
    
    # Default Pricing
    default_monthly_price = Column(String(50), nullable=True)  # e.g., "0", "99", "299", "custom"
    
    # Feature Flags (JSON object with feature: enabled)
    # Features: rbac_custom_roles, rbac_permissions, solarwinds, advanced_analytics, 
    #           api_access, webhook_access, white_labeling, on_premise, priority_support, etc.
    features = Column(JSON, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_plan = Column(Boolean, default=False, nullable=False)  # True for predefined plans
    is_custom = Column(Boolean, default=False, nullable=False)  # True for custom plans
    
    # Display order
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscriptions = relationship("TenantSubscription", back_populates="license_plan")
    
    # Indexes
    __table_args__ = (
        Index('idx_license_plan_key', 'plan_key'),
        Index('idx_license_plan_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<LicensePlan(plan_key='{self.plan_key}', plan_name='{self.plan_name}')>"
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if plan has a specific feature enabled"""
        if not self.features:
            return False
        return self.features.get(feature_name, False)




