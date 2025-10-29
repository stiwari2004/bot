"""
Search schemas
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    source_types: Optional[List[str]] = None


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    text: str
    score: float
    meta_data: Dict[str, Any]
    document_title: str
    document_source: str


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int

