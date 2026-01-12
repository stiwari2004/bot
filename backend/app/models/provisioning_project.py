"""
Provisioning Project model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class ProvisioningProject(Base):
    """Infrastructure provisioning project"""
    __tablename__ = "provisioning_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False, index=True)  # aws, azure, gcp, terraform
    template_id = Column(Integer, nullable=True)
    state = Column(String(50), nullable=False, default="pending", index=True)  # pending, provisioning, active, failed, destroyed
    terraform_state = Column(JSONB, nullable=True)
    variables = Column(JSONB, nullable=True)
    outputs = Column(JSONB, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    destroyed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", backref="provisioning_projects")
    creator = relationship("User", foreign_keys=[created_by])
    resources = relationship("ProvisionedResource", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProvisioningProject(id={self.id}, name='{self.name}', provider='{self.provider}', state='{self.state}')>"

