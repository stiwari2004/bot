"""
Discovery edge model - L3 dependency mapping.
Service endpoint to endpoint (or asset to asset) with confidence and evidence.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryEdge(Base):
    __tablename__ = "discovery_edges"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    from_asset_id = Column(Integer, ForeignKey("discovery_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_component_id = Column(Integer, ForeignKey("discovery_components.id", ondelete="CASCADE"), nullable=True, index=True)
    to_asset_id = Column(Integer, ForeignKey("discovery_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    to_component_id = Column(Integer, ForeignKey("discovery_components.id", ondelete="CASCADE"), nullable=True, index=True)
    edge_type = Column(String(50), nullable=False)  # tcp_connection, k8s_service, snmp_neighbor, etc.
    meta = Column(Text, nullable=True)  # JSON: port, protocol
    confidence = Column(String(20), nullable=True)
    evidence = Column(Text, nullable=True)  # JSON array

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant")
    run = relationship("DiscoveryRun", back_populates="edges")
    from_asset = relationship("DiscoveryAsset", foreign_keys=[from_asset_id])
    to_asset = relationship("DiscoveryAsset", foreign_keys=[to_asset_id])
    from_component = relationship("DiscoveryComponent", foreign_keys=[from_component_id])
    to_component = relationship("DiscoveryComponent", foreign_keys=[to_component_id])

    __table_args__ = (
        Index("idx_discovery_edges_tenant", "tenant_id"),
        Index("idx_discovery_edges_run", "run_id"),
        Index("idx_discovery_edges_from_asset", "from_asset_id"),
        Index("idx_discovery_edges_to_asset", "to_asset_id"),
    )

    def __repr__(self):
        return f"<DiscoveryEdge(id={self.id}, {self.from_asset_id}->{self.to_asset_id}, type='{self.edge_type}')>"
