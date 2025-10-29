"""
File upload and ingestion endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.schemas.upload import UploadResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and ingest a file"""
    try:
        ingestion_service = IngestionService()
        
        # Validate file type
        allowed_types = ["slack", "ticket", "log", "doc"]
        if source_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source type. Must be one of: {allowed_types}"
            )
        
        # Process the file
        result = await ingestion_service.process_file(
            file=file,
            source_type=source_type,
            title=title or file.filename,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        return UploadResponse(
            message="File uploaded and processed successfully",
            document_id=result["document_id"],
            chunks_created=result["chunks_created"],
            source_type=source_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/batch")
async def upload_batch(
    files: list[UploadFile] = File(...),
    source_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple files in batch"""
    try:
        ingestion_service = IngestionService()
        results = []
        
        for file in files:
            result = await ingestion_service.process_file(
                file=file,
                source_type=source_type,
                title=file.filename,
                tenant_id=current_user.tenant_id,
                db=db
            )
            results.append(result)
        
        return {
            "message": f"Successfully processed {len(files)} files",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

