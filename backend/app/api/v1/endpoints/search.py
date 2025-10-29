"""
Search endpoints for semantic search
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.vector_store import VectorStoreService

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform semantic search across documents"""
    try:
        vector_service = VectorStoreService()
        results = await vector_service.search(
            query=request.query,
            tenant_id=current_user.tenant_id,
            db=db,
            top_k=request.top_k or 10,
            source_types=request.source_types
        )
        
        # Convert SearchResult to SearchResult schema
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                text=result.text,
                score=result.score,
                meta_data=result.meta_data,
                document_title=result.document_title,
                document_source=result.document_source
            ))
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/suggest", response_model=List[str])
async def search_suggestions(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get search suggestions based on document titles"""
    from app.models.document import Document
    
    suggestions = db.query(Document.title).filter(
        Document.tenant_id == current_user.tenant_id,
        Document.title.contains(q)
    ).limit(10).all()
    
    return [suggestion[0] for suggestion in suggestions]

