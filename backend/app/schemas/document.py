"""
Document schemas
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    source_type: str
    title: str
    path: Optional[str]
    content_hash: str
    meta_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    skip: int
    limit: int

