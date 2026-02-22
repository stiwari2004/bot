"""
Central runbook library endpoints.
GET /central-runbooks - list library runbooks
POST /central-runbooks/{id}/import - copy to tenant
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.central_runbook import CentralRunbook
from app.models.runbook import Runbook
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=List[dict])
async def list_central_runbooks(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List runbooks from the central library.
    Optionally filter by category.
    """
    q = db.query(CentralRunbook).filter(CentralRunbook.is_active == True)
    if category:
        q = q.filter(CentralRunbook.category == category)
    runbooks = q.order_by(CentralRunbook.title).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "body_md": r.body_md,
            "meta_data": r.meta_data,
            "category": r.category,
            "version": r.version,
        }
        for r in runbooks
    ]


@router.post("/{central_runbook_id}/import", response_model=dict)
async def import_central_runbook(
    central_runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Copy a runbook from the central library into the current tenant's runbooks.
    Creates a new runbook with status draft.
    """
    central = db.query(CentralRunbook).filter(
        CentralRunbook.id == central_runbook_id,
        CentralRunbook.is_active == True,
    ).first()
    if not central:
        raise HTTPException(status_code=404, detail="Central runbook not found")

    runbook = Runbook(
        tenant_id=current_user.tenant_id,
        title=central.title,
        body_md=central.body_md,
        meta_data=central.meta_data,
        confidence=None,
        status="draft",
        is_active="draft",
        environment="production",
    )
    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(f"User {current_user.id} imported central runbook {central_runbook_id} as runbook {runbook.id}")

    return {
        "id": runbook.id,
        "title": runbook.title,
        "status": runbook.status,
        "message": "Runbook imported from central library",
    }
