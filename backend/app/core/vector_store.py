"""
Vector Store interface and implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import asyncio

from app.core.config import settings


@dataclass
class ChunkData:
    """Data structure for text chunks"""
    id: Optional[int] = None
    document_id: int = 0
    text: str = ""
    meta_data: Dict[str, Any] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.meta_data is None:
            self.meta_data = {}


@dataclass
class SearchResult:
    """Search result with similarity score"""
    chunk_id: int
    document_id: int
    text: str
    score: float
    meta_data: Dict[str, Any]
    document_title: str
    document_source: str


class VectorStore(ABC):
    """Abstract base class for vector store implementations"""
    
    @abstractmethod
    async def upsert_chunks(self, chunks: List[ChunkData], db: Session) -> None:
        """Upsert chunks and their embeddings"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        tenant_id: int, 
        top_k: int = 10,
        source_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Perform semantic search"""
        pass
    
    @abstractmethod
    async def delete_by_document(self, document_id: int, db: Session) -> None:
        """Delete all chunks and embeddings for a document"""
        pass


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector implementation"""
    
    def __init__(self):
        self.embedding_dim = settings.EMBEDDING_DIMENSION
        self._model = None
    
    def _get_model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (async wrapper for blocking operation)"""
        model = self._get_model()
        # Run blocking encode operation in thread pool
        embedding = await asyncio.to_thread(model.encode, [text])
        return embedding[0].tolist()
    
    def _vector_to_pg_format(self, vector: List[float]) -> str:
        """Convert vector to PostgreSQL vector format"""
        return f"[{','.join(map(str, vector))}]"
    
    def _vector_to_pg_cast(self, vector: List[float]) -> str:
        """Convert vector to PostgreSQL vector format with proper casting"""
        vector_str = f"[{','.join(map(str, vector))}]"
        return f"'{vector_str}'::vector"
    
    def _vector_to_pg_value(self, vector: List[float]) -> str:
        """Convert vector to PostgreSQL vector value without extra quotes"""
        return f"[{','.join(map(str, vector))}]"
    
    async def upsert_chunks(self, chunks: List[ChunkData], db: Session) -> None:
        """Upsert chunks and their embeddings"""
        from app.models.chunk import Chunk
        from app.models.embedding import Embedding
        
        for chunk_data in chunks:
            # Generate embedding if not provided
            if chunk_data.embedding is None:
                chunk_data.embedding = await self._generate_embedding(chunk_data.text)
            
            # Check if chunk already exists
            existing_chunk = db.query(Chunk).filter(
                Chunk.document_id == chunk_data.document_id,
                Chunk.text == chunk_data.text
            ).first()
            
            if existing_chunk:
                # Update existing chunk
                existing_chunk.meta_data = json.dumps(chunk_data.meta_data)
                
                # Update embedding
                embedding = db.query(Embedding).filter(
                    Embedding.chunk_id == existing_chunk.id
                ).first()
                
                if embedding:
                    embedding.embedding = chunk_data.embedding
                else:
                    # Create new embedding
                    new_embedding = Embedding(
                        chunk_id=existing_chunk.id,
                        embedding=chunk_data.embedding
                    )
                    db.add(new_embedding)
            else:
                # Create new chunk
                new_chunk = Chunk(
                    document_id=chunk_data.document_id,
                    text=chunk_data.text,
                    chunk_hash=hash(chunk_data.text),  # Simple hash for now
                    meta_data=json.dumps(chunk_data.meta_data)
                )
                db.add(new_chunk)
                db.flush()  # Get the ID
                
                # Create embedding
                new_embedding = Embedding(
                    chunk_id=new_chunk.id,
                    embedding=chunk_data.embedding
                )
                db.add(new_embedding)
        
        db.commit()
    
    async def search(
        self, 
        query: str, 
        tenant_id: int, 
        db: Session,
        top_k: int = 10,
        source_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Perform semantic search using pgvector"""
        from app.models.document import Document
        
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        query_vector = self._vector_to_pg_cast(query_embedding)
        
        # Build SQL query with proper vector casting
        sql = f"""
        SELECT 
            c.id as chunk_id,
            c.document_id,
            c.text,
            c.meta_data,
            d.title as document_title,
            d.source_type as document_source,
            1 - (e.embedding <=> {query_vector}) as score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        JOIN embeddings e ON c.id = e.chunk_id
        WHERE d.tenant_id = :tenant_id
        """
        
        params = {"tenant_id": tenant_id}
        
        if source_types:
            placeholders = ','.join([f':source_type_{i}' for i in range(len(source_types))])
            sql += f" AND d.source_type IN ({placeholders})"
            for i, source_type in enumerate(source_types):
                params[f"source_type_{i}"] = source_type
        
        sql += f" ORDER BY e.embedding <=> {query_vector} LIMIT :top_k"
        params["top_k"] = top_k
        
        # Execute query
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Convert to SearchResult objects
        results = []
        for row in rows:
            meta_data = json.loads(row.meta_data) if row.meta_data else {}
            
            results.append(SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                text=row.text,
                score=float(row.score),
                meta_data=meta_data,
                document_title=row.document_title,
                document_source=row.document_source
            ))
        
        return results
    
    async def delete_by_document(self, document_id: int, db: Session) -> None:
        """Delete all chunks and embeddings for a document"""
        from app.models.chunk import Chunk
        from app.models.embedding import Embedding
        
        # Get all chunk IDs for this document
        chunk_ids = db.query(Chunk.id).filter(
            Chunk.document_id == document_id
        ).all()
        
        chunk_ids = [chunk_id[0] for chunk_id in chunk_ids]
        
        if chunk_ids:
            # Delete embeddings
            db.query(Embedding).filter(
                Embedding.chunk_id.in_(chunk_ids)
            ).delete(synchronize_session=False)
            
            # Delete chunks
            db.query(Chunk).filter(
                Chunk.document_id == document_id
            ).delete(synchronize_session=False)
            
            db.commit()
    
    async def create_vector_index(self, db: Session) -> None:
        """Create vector similarity index for better performance"""
        sql = """
        CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
        ON embeddings USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100);
        """
        db.execute(text(sql))
        db.commit()
    
    async def hybrid_search(
        self,
        query: str,
        tenant_id: int,
        db: Session,
        top_k: int = 10,
        source_types: Optional[List[str]] = None,
        use_reranking: bool = True
    ) -> List[SearchResult]:
        """
        Hybrid search combining vector similarity + keyword search + optional reranking
        
        Strategy:
        1. Get top 2k results from vector search
        2. Get top 2k results from keyword (full-text) search  
        3. Merge and deduplicate
        4. Simple reranking: boost items that match in both
        5. Return top_k
        """
        from app.models.document import Document
        
        # Step 1: Vector search
        query_embedding = await self._generate_embedding(query)
        query_vector = self._vector_to_pg_cast(query_embedding)
        
        vector_sql = f"""
        SELECT 
            c.id as chunk_id,
            c.document_id,
            c.text,
            c.meta_data,
            d.title as document_title,
            d.source_type as document_source,
            1 - (e.embedding <=> {query_vector}) as vector_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        JOIN embeddings e ON c.id = e.chunk_id
        WHERE d.tenant_id = :tenant_id
        """
        
        params = {"tenant_id": tenant_id}
        
        if source_types:
            placeholders = ','.join([f':source_type_{i}' for i in range(len(source_types))])
            vector_sql += f" AND d.source_type IN ({placeholders})"
            for i, source_type in enumerate(source_types):
                params[f"source_type_{i}"] = source_type
        
        # Get 2x results for better recall
        vector_sql += f" ORDER BY e.embedding <=> {query_vector} LIMIT :top_k_expanded"
        params["top_k_expanded"] = top_k * 20  # Get 20x more for better coverage
        
        # Step 2: Keyword search using PostgreSQL full-text search
        keyword_sql = f"""
        SELECT 
            c.id as chunk_id,
            c.document_id,
            c.text,
            c.meta_data,
            d.title as document_title,
            d.source_type as document_source,
            ts_rank(to_tsvector('english', c.text), plainto_tsquery('english', :search_query)) as text_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.tenant_id = :tenant_id
        AND to_tsvector('english', c.text) @@ plainto_tsquery('english', :search_query)
        """
        
        if source_types:
            placeholders = ','.join([f':source_type_{i}' for i in range(len(source_types))])
            keyword_sql += f" AND d.source_type IN ({placeholders})"
        
        keyword_sql += " ORDER BY text_score DESC LIMIT :top_k_expanded_2"
        params["top_k_expanded_2"] = top_k * 20
        params["search_query"] = query
        
        # Execute both queries
        vector_result = db.execute(text(vector_sql), params)
        vector_rows = vector_result.fetchall()
        
        keyword_result = db.execute(text(keyword_sql), params)
        keyword_rows = keyword_result.fetchall()
        
        # Step 3: Merge and deduplicate results
        merged_results: Dict[int, SearchResult] = {}  # chunk_id -> SearchResult
        
        # Add vector results
        for row in vector_rows:
            meta_data = json.loads(row.meta_data) if row.meta_data else {}
            merged_results[row.chunk_id] = SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                text=row.text,
                score=float(row.vector_score),
                meta_data=meta_data,
                document_title=row.document_title,
                document_source=row.document_source
            )
        
        # Merge keyword results with scoring
        for row in keyword_rows:
            meta_data = json.loads(row.meta_data) if row.meta_data else {}
            keyword_score = float(row.text_score)
            
            if row.chunk_id in merged_results:
                # Found in both - boost the score (averaging approach)
                existing = merged_results[row.chunk_id]
                merged_results[row.chunk_id] = SearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    text=row.text,
                    score=(existing.score * 0.7) + (keyword_score * 0.3),  # Weight vector more
                    meta_data=meta_data,
                    document_title=row.document_title,
                    document_source=row.document_source
                )
            else:
                # Keyword-only result - add with lower weight
                merged_results[row.chunk_id] = SearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    text=row.text,
                    score=keyword_score * 0.5,  # Keyword-only gets lower weight
                    meta_data=meta_data,
                    document_title=row.document_title,
                    document_source=row.document_source
                )
        
        # Step 4: Sort by combined score and return top_k
        sorted_results = sorted(merged_results.values(), key=lambda x: x.score, reverse=True)
        
        return sorted_results[:top_k]
