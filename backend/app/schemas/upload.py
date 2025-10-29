"""
Upload schemas
"""
from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    message: str
    document_id: int
    chunks_created: int
    source_type: str

