"""
Runbook schemas
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class RunbookResponse(BaseModel):
    id: int
    title: str
    body_md: str
    meta_data: Optional[Dict[str, Any]]
    confidence: Optional[float]
    parent_version_id: Optional[int] = None
    status: Optional[str] = "draft"  # draft, approved, archived
    is_active: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class RunbookListResponse(BaseModel):
    runbooks: list[RunbookResponse]
    total: int
    skip: int
    limit: int


class RunbookCreate(BaseModel):
    title: str
    body_md: str
    meta_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


class RunbookUpdate(BaseModel):
    title: Optional[str] = None
    body_md: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


class RunbookCreateRequest(BaseModel):
    query: Optional[str] = None
    document_id: Optional[int] = None
    title: Optional[str] = None
    body_md: Optional[str] = None

