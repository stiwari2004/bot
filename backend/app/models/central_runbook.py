"""
Central runbook model - Resolvify-hosted library for import into tenant runbooks
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class CentralRunbook(Base):
    __tablename__ = "central_runbooks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    body_md = Column(Text, nullable=False)
    meta_data = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CentralRunbook(id={self.id}, title='{self.title}')>"
