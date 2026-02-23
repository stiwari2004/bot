"""
PaaS synced user model (central only).
Users synced from edge for billing; upserted by (tenant_id, email).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class PaasSyncedUser(Base):
    __tablename__ = "paas_synced_users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_user_id = Column(Integer, nullable=True)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True)
    node_details = Column(JSONB, nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source = Column(String(50), nullable=False, default="paas_edge")
