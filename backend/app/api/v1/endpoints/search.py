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
from app.core.rate_limiting import rate_limit

router = APIRouter()


@router.post("/", response_model=SearchResponse)
@rate_limit("100/minute")  # High limit for dev/test
async def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform semantic search across documents (cached)"""
    from app.core.cache import cache_service, cache_key
    
    try:
        # Generate cache key from search parameters
        cache_key_str = cache_key(
            "search:semantic",
            current_user.tenant_id,
            request.query,
            request.top_k or 10,
            request.source_types or []
        )
        
        # Try to get from cache
        cached_result = await cache_service.get(cache_key_str)
        if cached_result is not None:
            return SearchResponse(**cached_result)
        
        # Perform search
        vector_service = VectorStoreService()
        results = await vector_service.hybrid_search(
            query=request.query,
            tenant_id=current_user.tenant_id,
            db=db,
            top_k=request.top_k or 10,
            source_types=request.source_types,
            use_reranking=True
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
        
        response = SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results)
        )
        
        # Cache for 15 minutes
        await cache_service.set(cache_key_str, response.dict(), ttl=900)
        
        return response
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

