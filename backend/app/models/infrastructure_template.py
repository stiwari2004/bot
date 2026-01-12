"""
Infrastructure Template model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class InfrastructureTemplate(Base):
    """Reusable infrastructure template (Terraform, CloudFormation, Ansible)"""
    __tablename__ = "infrastructure_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False, index=True)
    template_type = Column(String(50), nullable=True, index=True)  # server, web_app, kubernetes, network
    template_content = Column(Text, nullable=False)  # Terraform/CloudFormation/Ansible code
    variables_schema = Column(JSONB, nullable=True)
    is_public = Column(Boolean, default=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", backref="infrastructure_templates")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<InfrastructureTemplate(id={self.id}, name='{self.name}', provider='{self.provider}', type='{self.template_type}')>"

