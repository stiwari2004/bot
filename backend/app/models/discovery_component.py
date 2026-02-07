"""
Discovery component model - L2 component inventory.
Service endpoint on an asset (e.g. Postgres, Redis) with confidence and evidence.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryComponent(Base):
    __tablename__ = "discovery_components"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("discovery_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    component_type = Column(String(80), nullable=False)  # postgres, redis, nginx, app, k8s_deployment, etc.
    bind_address = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    meta = Column(Text, nullable=True)  # JSON
    confidence = Column(String(20), nullable=True)  # high, medium, low (or 0-1 scale stored as string)
    evidence = Column(Text, nullable=True)  # JSON array of how we inferred this component

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant")
    asset = relationship("DiscoveryAsset", back_populates="components")
    run = relationship("DiscoveryRun", back_populates="components")
    edges_from = relationship("DiscoveryEdge", back_populates="from_component", foreign_keys="DiscoveryEdge.from_component_id")
    edges_to = relationship("DiscoveryEdge", back_populates="to_component", foreign_keys="DiscoveryEdge.to_component_id")

    __table_args__ = (
        Index("idx_discovery_components_tenant", "tenant_id"),
        Index("idx_discovery_components_asset", "asset_id"),
        Index("idx_discovery_components_run", "run_id"),
    )

    def __repr__(self):
        return f"<DiscoveryComponent(id={self.id}, type='{self.component_type}', asset_id={self.asset_id})>"
