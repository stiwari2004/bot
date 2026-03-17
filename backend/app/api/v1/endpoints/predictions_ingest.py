"""
Predictions — log ingestion endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.core.logging import get_logger

try:
    from app.services.prediction.log_ingestion_service import LogIngestionService
except ImportError:
    LogIngestionService = None

logger = get_logger(__name__)
router = APIRouter()


class LogIngestionRequest(BaseModel):
    logs: List[Dict[str, Any]]
    source: str


class WindowsEventLogRequest(BaseModel):
    log_name: str = "Application"
    max_events: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class LinuxSyslogRequest(BaseModel):
    log_type: str = "syslog"
    lines: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class JournaldRequest(BaseModel):
    unit: Optional[str] = None
    lines: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    ssh_key_path: Optional[str] = None


@router.post("/ingest", response_model=Dict[str, Any])
async def ingest_logs(
    request: LogIngestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from API"""
    try:
        if LogIngestionService is None:
            raise HTTPException(status_code=503, detail="Log ingestion service not available")
        result = await LogIngestionService().ingest_from_api(
            logs=request.logs, source=request.source,
            tenant_id=current_user.tenant_id, db=db
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/windows-eventlog")
async def ingest_windows_eventlog(
    request: WindowsEventLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from Windows Event Log"""
    try:
        if LogIngestionService is None:
            raise HTTPException(status_code=503, detail="Log ingestion service not available")
        return await LogIngestionService().ingest_from_windows_eventlog(
            log_name=request.log_name, max_events=request.max_events,
            host=request.host, username=request.username, password=request.password,
            tenant_id=current_user.tenant_id, db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting Windows Event Log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/linux-syslog")
async def ingest_linux_syslog(
    request: LinuxSyslogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from Linux syslog"""
    try:
        if LogIngestionService is None:
            raise HTTPException(status_code=503, detail="Log ingestion service not available")
        return await LogIngestionService().ingest_from_linux_syslog(
            log_type=request.log_type, lines=request.lines,
            host=request.host, username=request.username, ssh_key_path=request.ssh_key_path,
            tenant_id=current_user.tenant_id, db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting Linux syslog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/journald")
async def ingest_journald(
    request: JournaldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from systemd journal (journalctl)"""
    try:
        if LogIngestionService is None:
            raise HTTPException(status_code=503, detail="Log ingestion service not available")
        return await LogIngestionService().ingest_from_journald(
            unit=request.unit, lines=request.lines,
            host=request.host, username=request.username, ssh_key_path=request.ssh_key_path,
            tenant_id=current_user.tenant_id, db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting journald logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
