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
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        model = self._get_model()
        embedding = model.encode([text])[0]
        return embedding.tolist()
    
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
                chunk_data.embedding = self._generate_embedding(chunk_data.text)
            
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
                    embedding.embedding = self._vector_to_pg_value(chunk_data.embedding)
                else:
                    # Create new embedding
                    new_embedding = Embedding(
                        chunk_id=existing_chunk.id,
                        embedding=self._vector_to_pg_value(chunk_data.embedding)
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
                    embedding=self._vector_to_pg_value(chunk_data.embedding)
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
        query_embedding = self._generate_embedding(query)
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
