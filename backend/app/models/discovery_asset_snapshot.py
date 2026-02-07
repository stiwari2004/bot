"""
Discovery asset snapshot - optional history snapshot of asset attributes at a run.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryAssetSnapshot(Base):
    __tablename__ = "discovery_asset_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("discovery_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot = Column(Text, nullable=True)  # JSON snapshot of asset attributes at run time

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("DiscoveryRun")
    asset = relationship("DiscoveryAsset")

    __table_args__ = (
        Index("idx_discovery_asset_snapshots_run", "run_id"),
        Index("idx_discovery_asset_snapshots_asset", "asset_id"),
    )

    def __repr__(self):
        return f"<DiscoveryAssetSnapshot(id={self.id}, run_id={self.run_id}, asset_id={self.asset_id})>"
