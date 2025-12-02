"""
File upload and ingestion endpoints (MF-12: Comprehensive validation)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.services.auth import get_current_user
from app.schemas.upload import UploadResponse
from app.services.ingestion import IngestionService
from app.core.rate_limiting import rate_limit

router = APIRouter()

# Allowed file extensions and MIME types (MF-12)
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".pdf", ".doc", ".docx"}
ALLOWED_MIME_TYPES = {
    "text/plain", "text/markdown", "text/csv", "application/json",
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

# Dangerous file patterns to reject (MF-12)
DANGEROUS_PATTERNS = [
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".jar",
    ".dll", ".so", ".dylib", ".scr", ".com", ".pif", ".app"
]


def validate_file_upload(file: UploadFile) -> None:
    """Comprehensive file upload validation (MF-12)"""
    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.MAX_FILE_SIZE} bytes)"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Check file extension
    if file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext in DANGEROUS_PATTERNS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_ext}' is not allowed for security reasons"
            )
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{file_ext}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
    
    # Check MIME type (if available)
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in ALLOWED_MIME_TYPES:
            # Try to detect actual MIME type using python-magic if available
            if MAGIC_AVAILABLE:
                try:
                    file_content = file.file.read(1024)  # Read first 1KB
                    file.file.seek(0)
                    detected_mime = magic.from_buffer(file_content, mime=True)
                    if detected_mime not in ALLOWED_MIME_TYPES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"File MIME type '{detected_mime}' is not allowed"
                        )
                except Exception:
                    # If magic detection fails, allow if extension is valid
                    pass
            else:
                # python-magic not available, rely on content_type
                if file.content_type not in ALLOWED_MIME_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File MIME type '{file.content_type}' is not allowed"
                    )


@router.post("/", response_model=UploadResponse)
@rate_limit("50/minute")  # Moderate limit for file uploads
async def upload_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and ingest a file (MF-12: Comprehensive validation)"""
    try:
        # Validate file upload (MF-12)
        validate_file_upload(file)
        
        ingestion_service = IngestionService()
        
        # Validate file type
        allowed_types = ["slack", "ticket", "jira", "servicenow", "log", "doc"]
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/batch")
@rate_limit("20/minute")  # Lower limit for batch uploads
async def upload_batch(
    files: list[UploadFile] = File(...),
    source_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple files in batch (MF-12: Comprehensive validation)"""
    try:
        # Validate all files first (MF-12)
        for file in files:
            validate_file_upload(file)
        
        # Validate file type
        allowed_types = ["slack", "ticket", "jira", "servicenow", "log", "doc"]
        if source_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source type. Must be one of: {allowed_types}"
            )
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

