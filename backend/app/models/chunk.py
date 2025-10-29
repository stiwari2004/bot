"""
Chunk model for text chunks
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    chunk_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    meta_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_hash', 'chunk_hash'),
    )
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, document_id={self.document_id}, text_length={len(self.text)})>"

