"""
Provisioned Resource model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class ProvisionedResource(Base):
    """Individual resource created by a provisioning project"""
    __tablename__ = "provisioned_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("provisioning_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)  # instance, network, load_balancer, etc.
    resource_id = Column(String(255), nullable=False)  # Cloud provider resource ID
    name = Column(String(255), nullable=True)
    provider = Column(String(50), nullable=False)
    region = Column(String(100), nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("ProvisioningProject", back_populates="resources")
    
    def __repr__(self):
        return f"<ProvisionedResource(id={self.id}, type='{self.resource_type}', resource_id='{self.resource_id}')>"

