"""
Discovery asset model - L1 asset inventory.
Identity by (source, source_native_id) or fingerprint; IPs are attributes.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryAsset(Base):
    __tablename__ = "discovery_assets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # azure, aws, gcp, vcenter, hyperv, discovered_via_connection, external_endpoint
    source_native_id = Column(String(512), nullable=False)  # Stable ID from source (e.g. Azure resource ID, vCenter VM id)
    fingerprint = Column(String(512), nullable=True)  # For connection-discovered: hostname+FQDN, MAC, or fallback
    primary_ip = Column(String(45), nullable=True)
    ips = Column(Text, nullable=True)  # JSON array of IPs
    name = Column(String(255), nullable=True)
    tags = Column(Text, nullable=True)  # JSON: owner, env, etc.
    current_run_id = Column(Integer, ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="discovery_assets")
    current_run = relationship("DiscoveryRun", back_populates="assets", foreign_keys=[current_run_id])
    components = relationship("DiscoveryComponent", back_populates="asset", cascade="all, delete-orphan")
    edges_from = relationship("DiscoveryEdge", back_populates="from_asset", foreign_keys="DiscoveryEdge.from_asset_id")
    edges_to = relationship("DiscoveryEdge", back_populates="to_asset", foreign_keys="DiscoveryEdge.to_asset_id")

    __table_args__ = (
        Index("idx_discovery_assets_tenant", "tenant_id"),
        Index("idx_discovery_assets_source", "source"),
        Index("idx_discovery_assets_primary_ip", "primary_ip"),
        UniqueConstraint("tenant_id", "source", "source_native_id", name="uq_discovery_asset_tenant_source_native"),
    )

    def __repr__(self):
        return f"<DiscoveryAsset(id={self.id}, name='{self.name}', source='{self.source}')>"
