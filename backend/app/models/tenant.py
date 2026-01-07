"""
Tenant model for multi-tenant support
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    subdomain_slug = Column(String(100), unique=True, nullable=True, index=True)  # For future subdomain routing
    description = Column(Text, nullable=True)
    
    # Deployment type
    deployment_type = Column(String(20), nullable=False, default='saas')  # 'saas' or 'paas'
    platform_managed = Column(Boolean, default=True)  # True for SaaS, False for PaaS
    
    # PaaS-specific (self-hosted)
    setup_token = Column(String(255), unique=True, nullable=True, index=True)
    setup_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    setup_completed_at = Column(DateTime(timezone=True), nullable=True)
    self_hosted_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    onboarding_status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    
    # Contact info
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # Configuration metadata (JSON)
    config_metadata = Column(JSON, nullable=True)  # Store limits, features, connection configs, etc.
    
    # White-labeling / MSP support
    is_msp = Column(Boolean, default=False, nullable=False)  # Is this tenant an MSP that can create sub-tenants?
    parent_tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)  # If sub-tenant, reference parent MSP
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    tickets = relationship("Ticket", back_populates="tenant")
    billing_config = relationship("TenantBillingConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("TenantSubscription", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    parent_tenant = relationship("Tenant", remote_side=[id], backref="sub_tenants")
    change_tickets = relationship("ChangeTicket", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', type='{self.deployment_type}')>"

