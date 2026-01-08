"""
User model for authentication and authorization
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

# Import RBAC models to ensure they're registered before User relationships are set up
try:
    from app.models.role import Role
    from app.models.user_permission import UserPermission
except ImportError:
    # RBAC models not available - relationships will be set up later
    Role = None
    UserPermission = None


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Role system - supports both legacy string role and new RBAC role_id
    role = Column(String(50), default="user")  # Legacy: user, viewer, tenant_admin, msp_admin, super_admin (legacy: admin)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True)  # New RBAC system
    
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)  # Force password change at next login
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset fields
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True, index=True)
    
    # Password history and expiration
    password_history = Column(JSONB, nullable=True)  # JSON array of password hashes
    password_expires_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Account lockout fields
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)
    last_failed_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Profile fields
    avatar_url = Column(String(500), nullable=True)
    phone_number = Column(String(50), nullable=True)
    department = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    timezone = Column(String(50), default='UTC')
    locale = Column(String(10), default='en-US')
    
    # Preferences (JSONB)
    preferences = Column(JSONB, nullable=True, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    # RBAC relationships - lazy loaded to avoid errors if tables don't exist
    role_obj = relationship("Role", foreign_keys=[role_id], back_populates="users", lazy="select", uselist=False)
    user_permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan", lazy="select")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tenant_id={self.tenant_id}, role_id={self.role_id})>"

