"""
Credential model for storing infrastructure credentials
POC version - simplified, stored in database (encrypted)
For production, migrate to HashiCorp Vault or similar
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Credential(Base):
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Descriptive name
    credential_type = Column(String(50), nullable=False)  # ssh, api_key, database, aws, azure, gcp
    environment = Column(String(20), nullable=False)  # prod, staging, dev
    username = Column(String(255), nullable=True)  # For SSH, database, etc.
    # Note: Password/secret stored encrypted (use Fernet encryption)
    encrypted_password = Column(Text, nullable=True)  # Encrypted password/secret
    encrypted_api_key = Column(Text, nullable=True)  # Encrypted API key
    host = Column(String(255), nullable=True)  # Host/IP for SSH
    port = Column(Integer, nullable=True)  # Port number
    database_name = Column(String(255), nullable=True)  # For database credentials
    connection_string = Column(Text, nullable=True)  # Encrypted connection string
    meta_data = Column(Text, nullable=True)  # JSON string with additional info (renamed from metadata)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    infrastructure_connections = relationship("InfrastructureConnection", back_populates="credential")
    
    # Indexes
    __table_args__ = (
        Index('idx_credentials_tenant', 'tenant_id'),
        Index('idx_credentials_type', 'credential_type'),
        Index('idx_credentials_env', 'environment'),
    )
    
    def __repr__(self):
        return f"<Credential(id={self.id}, name='{self.name}', type='{self.credential_type}')>"


class InfrastructureConnection(Base):
    """Define infrastructure connections (which credential to use for which target)"""
    __tablename__ = "infrastructure_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(Integer, ForeignKey("credentials.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Descriptive name
    connection_type = Column(String(50), nullable=False)  # ssh, database, api, cloud
    target_host = Column(String(255), nullable=True)  # Host/IP
    target_port = Column(Integer, nullable=True)  # Port
    target_service = Column(String(255), nullable=True)  # Service name (e.g., "postgres", "mysql")
    environment = Column(String(20), nullable=False)  # prod, staging, dev
    meta_data = Column(Text, nullable=True)  # JSON string with additional info (renamed from metadata)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    credential = relationship("Credential", back_populates="infrastructure_connections")
    
    # Indexes
    __table_args__ = (
        Index('idx_infrastructure_connections_tenant', 'tenant_id'),
        Index('idx_infrastructure_connections_type', 'connection_type'),
        Index('idx_infrastructure_connections_host', 'target_host'),
    )
    
    def __repr__(self):
        return f"<InfrastructureConnection(id={self.id}, name='{self.name}', type='{self.connection_type}')>"

