"""
Inquiry model for trial intake submissions from marketing site
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)
    infrastructure_type = Column(String(50), nullable=True)
    itsm_tools = Column(Text, nullable=True)  # JSON array as text
    monitoring_tools = Column(Text, nullable=True)  # JSON array as text
    top_incident_pain = Column(String(100), nullable=True)
    node_count_estimate = Column(String(50), nullable=True)
    status = Column(String(50), default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Inquiry(id={self.id}, email='{self.email}', status='{self.status}')>"
