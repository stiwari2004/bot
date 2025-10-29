"""
Document model for source documents
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # slack, ticket, log, doc
    title = Column(String(500), nullable=False)
    path = Column(String(1000), nullable=True)  # file path or URL
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    meta_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_documents_tenant_source', 'tenant_id', 'source_type'),
        Index('idx_documents_content_hash', 'content_hash'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', source_type='{self.source_type}')>"

