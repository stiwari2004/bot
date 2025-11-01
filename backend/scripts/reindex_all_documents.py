#!/usr/bin/env python3
"""
Reindex all documents with new embedding model
This script reads all chunks and regenerates their embeddings
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.vector_store import PgVectorStore, ChunkData
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.document import Document
from app.models.tenant import Tenant  # Import to resolve relationships
from app.models.user import User  # Import to resolve relationships


async def reindex_all_documents():
    """Reindex all documents with new embedding model"""
    db: Session = SessionLocal()
    try:
        # Initialize vector store (will use new model from config)
        vector_store = PgVectorStore()
        
        print("🔄 Starting reindex with new embedding model...")
        print(f"📊 Model: {vector_store._get_model()}")
        print(f"📏 Dimensions: {vector_store.embedding_dim}")
        print()
        
        # Get all chunks
        chunks = db.query(Chunk).all()
        print(f"📚 Found {len(chunks)} chunks to reindex")
        
        # Process in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            chunk_data_objects = []
            
            for chunk in batch:
                # Delete old embedding
                db.query(Embedding).filter(Embedding.chunk_id == chunk.id).delete()
                
                # Create ChunkData for re-indexing
                chunk_data_objects.append(ChunkData(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    text=chunk.text,
                    meta_data={}  # Will be filled from existing metadata
                ))
            
            # Upsert with new embeddings
            await vector_store.upsert_chunks(chunk_data_objects, db)
            db.commit()
            
            print(f"✅ Processed batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size} ({min(i + batch_size, len(chunks))}/{len(chunks)} chunks)")
        
        print()
        print("✅ Reindex complete!")
        print(f"📊 Total embeddings: {db.query(Embedding).count()}")
        
    except Exception as e:
        print(f"❌ Error during reindex: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(reindex_all_documents())

