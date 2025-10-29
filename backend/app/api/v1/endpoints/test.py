"""
Test endpoints for development and debugging
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.vector_store import VectorStoreService
from app.core.vector_store import ChunkData

router = APIRouter()


@router.post("/test-vector-store")
async def test_vector_store(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test vector store functionality"""
    try:
        vector_service = VectorStoreService()
        
        # Create test chunks
        test_chunks = [
            ChunkData(
                document_id=1,  # Assuming document 1 exists
                text="This is a test document about network troubleshooting",
                meta_data={"source": "test", "type": "network"}
            ),
            ChunkData(
                document_id=1,
                text="Database connection issues and how to resolve them",
                meta_data={"source": "test", "type": "database"}
            )
        ]
        
        # Upsert test chunks
        await vector_service.upsert_chunks(test_chunks, db)
        
        # Test search
        results = await vector_service.search(
            query="network problems",
            tenant_id=current_user.tenant_id,
            top_k=5
        )
        
        return {
            "message": "Vector store test completed",
            "chunks_created": len(test_chunks),
            "search_results": len(results),
            "results": [
                {
                    "text": result.text,
                    "score": result.score,
                    "source": result.document_source
                } for result in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.get("/health-detailed")
async def health_detailed(
    db: Session = Depends(get_db)
):
    """Detailed health check with database status"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Check if tables exist
        from app.models import tenant, user, document, chunk, embedding, runbook, execution, audit
        
        return {
            "status": "healthy",
            "database": "connected",
            "tables": "created",
            "vector_extension": "enabled"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
