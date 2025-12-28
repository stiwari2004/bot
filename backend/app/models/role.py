"""
Role model for RBAC system
Roles can be predefined (system roles) or custom (user-created)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "viewer", "custom_role_1"
    display_name = Column(String(255), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    
    # Role type
    is_system_role = Column(Boolean, default=False)  # True for predefined roles (viewer, user, etc.)
    is_custom = Column(Boolean, default=False)  # True for user-created custom roles
    
    # Scope
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)  # None = global role
    is_global = Column(Boolean, default=True)  # True if role applies to all tenants
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role_obj")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', is_system={self.is_system_role}, is_custom={self.is_custom})>"

