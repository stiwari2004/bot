"""
Embedding model for vector embeddings using pgvector
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings


class Embedding(Base):
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=False, index=True)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chunk = relationship("Chunk", back_populates="embeddings")
    
    # Indexes for vector similarity search
    __table_args__ = (
        Index('idx_embeddings_chunk', 'chunk_id'),
        # Vector similarity index will be created via SQL
    )
    
    def __repr__(self):
        return f"<Embedding(id={self.id}, chunk_id={self.chunk_id})>"

