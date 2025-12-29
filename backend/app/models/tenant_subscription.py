"""
Tenant subscription/license model
Tracks seats (users) and nodes (infrastructure) limits with enforcement
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class TenantSubscription(Base):
    """Subscription assigned to a tenant with seat and node limits"""
    __tablename__ = "tenant_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # License Plan Reference
    license_plan_id = Column(Integer, ForeignKey("license_plans.id", ondelete="SET NULL"), nullable=True, index=True, comment="Reference to license plan (Free, Starter, etc.)")
    
    # Subscription Limits
    max_seats = Column(Integer, nullable=False, comment="Maximum number of user seats allowed")
    max_nodes = Column(Integer, nullable=False, comment="Maximum number of infrastructure nodes allowed")
    
    # Current Usage (snapshot, updated periodically)
    current_seats = Column(Integer, default=0, nullable=False, comment="Current number of active users")
    current_nodes = Column(Integer, default=0, nullable=False, comment="Current number of active infrastructure connections")
    
    # Subscription Details
    subscription_name = Column(String(255), nullable=True, comment="Custom subscription name")
    monthly_price = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Monthly subscription price")
    
    # Overage Rates (if limits exceeded)
    seat_overage_rate = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per additional seat per month")
    node_overage_rate = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per additional node per month")
    
    # Status
    status = Column(String(20), default="active", nullable=False, comment="active, suspended, expired, cancelled")
    is_enforced = Column(Boolean, default=True, nullable=False, comment="If true, enforce limits and block when exceeded")
    
    # Dates
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="NULL = never expires")
    auto_renew = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    notes = Column(String(500), nullable=True, comment="Admin notes about this subscription")
    created_by = Column(Integer, ForeignKey("super_admins.id", ondelete="SET NULL"), nullable=True, comment="Super admin who created this")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    license_plan = relationship("LicensePlan", back_populates="subscriptions")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_tenant', 'tenant_id'),
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_enforced', 'is_enforced'),
    )
    
    def __repr__(self):
        return f"<TenantSubscription(tenant_id={self.tenant_id}, seats={self.current_seats}/{self.max_seats}, nodes={self.current_nodes}/{self.max_nodes})>"
    
    @property
    def seats_remaining(self) -> int:
        """Calculate remaining seats"""
        return max(0, self.max_seats - self.current_seats)
    
    @property
    def nodes_remaining(self) -> int:
        """Calculate remaining nodes"""
        return max(0, self.max_nodes - self.current_nodes)
    
    @property
    def seats_exceeded(self) -> bool:
        """Check if seats limit exceeded"""
        return self.current_seats > self.max_seats
    
    @property
    def nodes_exceeded(self) -> bool:
        """Check if nodes limit exceeded"""
        return self.current_nodes > self.max_nodes
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active"""
        if self.status != "active":
            return False
        if self.expires_at:
            from datetime import datetime, timezone
            return datetime.now(timezone.utc) < self.expires_at
        return True


class SubscriptionUsage(Base):
    """Track subscription usage over time for reporting"""
    __tablename__ = "subscription_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("tenant_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Peak Usage (highest during period)
    peak_seats = Column(Integer, default=0, nullable=False)
    peak_nodes = Column(Integer, default=0, nullable=False)
    
    # Average Usage
    avg_seats = Column(Numeric(10, 2), default=0.00, nullable=False)
    avg_nodes = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Overage
    seat_overage_days = Column(Integer, default=0, nullable=False, comment="Number of days seats limit was exceeded")
    node_overage_days = Column(Integer, default=0, nullable=False, comment="Number of days nodes limit was exceeded")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_subscription_period', 'subscription_id', 'period_start', 'period_end'),
        Index('idx_usage_tenant_period', 'tenant_id', 'period_start', 'period_end'),
    )


