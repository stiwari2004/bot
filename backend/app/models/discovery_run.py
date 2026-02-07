"""
Discovery run model - first-class entity for each discovery execution.
Deterministic, debuggable runs with run_config and stage_log.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    run_config = Column(Text, nullable=True)  # JSON: connector ref, scope, scanner mode
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), nullable=False, default="running")  # running, success, failed, cancelled
    stage_log = Column(Text, nullable=True)  # JSON: stages and per-stage status/log
    artifact_ref = Column(Text, nullable=True)  # Optional ref to raw payload storage (e.g. blob path)

    # Relationships
    tenant = relationship("Tenant", backref="discovery_runs")
    assets = relationship("DiscoveryAsset", back_populates="current_run", foreign_keys="DiscoveryAsset.current_run_id")
    components = relationship("DiscoveryComponent", back_populates="run")
    edges = relationship("DiscoveryEdge", back_populates="run")

    __table_args__ = (
        Index("idx_discovery_runs_tenant", "tenant_id"),
        Index("idx_discovery_runs_status", "status"),
        Index("idx_discovery_runs_started", "started_at"),
    )

    def __repr__(self):
        return f"<DiscoveryRun(id={self.id}, tenant_id={self.tenant_id}, status='{self.status}')>"
