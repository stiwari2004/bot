"""
Vector store service for semantic search
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.vector_store import PgVectorStore, ChunkData
from app.schemas.search import SearchResult


class VectorStoreService:
    """Service for vector operations using Postgres + pgvector"""
    
    def __init__(self):
        self.vector_store = PgVectorStore()
    
    async def search(
        self, 
        query: str, 
        tenant_id: int, 
        db: Session,
        top_k: int = 10,
        source_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Perform semantic search"""
        return await self.vector_store.search(
            query=query,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=source_types
        )
    
    async def hybrid_search(
        self, 
        query: str, 
        tenant_id: int, 
        db: Session,
        top_k: int = 10,
        source_types: Optional[List[str]] = None,
        use_reranking: bool = True
    ) -> List[SearchResult]:
        """Perform hybrid search (vector + keyword + reranking)"""
        return await self.vector_store.hybrid_search(
            query=query,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=source_types,
            use_reranking=use_reranking
        )
    
    async def upsert_chunks(self, chunks: List[ChunkData], db: Session) -> None:
        """Upsert chunks and their embeddings"""
        await self.vector_store.upsert_chunks(chunks, db)
    
    async def delete_by_document(self, document_id: int, db: Session) -> None:
        """Delete all chunks and embeddings for a document"""
        await self.vector_store.delete_by_document(document_id, db)
    
    async def create_index(self, db: Session) -> None:
        """Create vector similarity index"""
        await self.vector_store.create_vector_index(db)

