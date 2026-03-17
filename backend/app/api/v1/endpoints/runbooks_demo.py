"""
Runbook demo CRUD, step review, and utility endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.runbook import RunbookResponse, RunbookUpdate, RunbookFeedbackRequest
from app.services.auth import get_current_user
from app.controllers.runbook_controller import RunbookController
from app.api.v1.endpoints.runbooks_schemas import (
    RunbookStepApproveBody, RunbookStepCommandBody, RunbookStepRegenerateBody
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/demo", response_model=List[RunbookResponse])
@router.get("/demo/", response_model=List[RunbookResponse])
async def list_runbooks_demo(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List runbooks for the authenticated user's tenant"""
    try:
        result = RunbookController(db, tenant_id=current_user.tenant_id).list_runbooks(skip, limit)
        return result if isinstance(result, list) else []
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in list_runbooks_demo: {e}", exc_info=True)
        return []


@router.get("/demo/{runbook_id}", response_model=RunbookResponse)
async def get_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific runbook by ID for the authenticated user's tenant"""
    return RunbookController(db, tenant_id=current_user.tenant_id).get_runbook(runbook_id)


@router.put("/demo/{runbook_id}", response_model=RunbookResponse)
async def update_runbook_demo(
    runbook_id: int,
    runbook_update: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a demo runbook for the authenticated user's tenant."""
    from app.core.cache import cache_service, cache_key
    controller = RunbookController(db, tenant_id=current_user.tenant_id)
    result = controller.update_runbook(runbook_id, runbook_update)
    await cache_service.delete(cache_key("runbook:get", runbook_id, current_user.tenant_id))
    await cache_service.delete_pattern(f"runbooks:list:{current_user.tenant_id}:*")
    return result


@router.delete("/demo/{runbook_id}")
async def delete_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a runbook for the authenticated user's tenant (soft delete)"""
    return RunbookController(db, tenant_id=current_user.tenant_id).delete_runbook(runbook_id)


@router.post("/demo/{runbook_id}/approve", response_model=RunbookResponse)
async def approve_runbook_demo(
    runbook_id: int,
    force_approval: bool = False,
    ticket_id: Optional[int] = Query(None, description="Optional ticket ID to associate runbook with"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve and publish a draft runbook with duplicate detection"""
    return await RunbookController(db, tenant_id=current_user.tenant_id).approve_runbook(
        runbook_id, force_approval, ticket_id
    )


@router.get("/demo/{runbook_id}/review-status")
async def get_runbook_review_status_demo(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get command review status."""
    return RunbookController(db, tenant_id=current_user.tenant_id).get_review_status(runbook_id)


@router.post("/demo/{runbook_id}/steps/approve", response_model=RunbookResponse)
async def runbook_step_approve_demo(
    runbook_id: int,
    body: RunbookStepApproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a step as approved by human."""
    return RunbookController(db, tenant_id=current_user.tenant_id).approve_step(runbook_id, body.section, body.index)


@router.put("/demo/{runbook_id}/steps/command", response_model=RunbookResponse)
async def runbook_step_update_command_demo(
    runbook_id: int,
    body: RunbookStepCommandBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a step's command."""
    return RunbookController(db, tenant_id=current_user.tenant_id).update_step_command(
        runbook_id, body.section, body.index, body.command
    )


@router.post("/demo/{runbook_id}/steps/regenerate", response_model=RunbookResponse)
async def runbook_step_regenerate_demo(
    runbook_id: int,
    body: RunbookStepRegenerateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a single step's command with optional human context."""
    return await RunbookController(db, tenant_id=current_user.tenant_id).regenerate_step_command(
        runbook_id, body.section, body.index, body.human_context
    )


@router.post("/demo/{runbook_id}/feedback", response_model=RunbookResponse)
async def runbook_step_feedback_demo(
    runbook_id: int,
    body: RunbookFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply human step-level feedback to a runbook."""
    return await RunbookController(db, tenant_id=current_user.tenant_id).apply_step_feedback(runbook_id, body)


@router.post("/demo/{runbook_id}/reindex")
async def reindex_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually reindex an already approved runbook."""
    return await RunbookController(db, tenant_id=current_user.tenant_id).reindex_runbook(runbook_id)


@router.post("/demo/{runbook_id}/associate-ticket")
async def associate_runbook_with_ticket_demo(
    runbook_id: int,
    ticket_id: int = Query(..., description="Ticket ID to associate with"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually associate a runbook with a ticket."""
    controller = RunbookController(db, tenant_id=current_user.tenant_id)
    success = controller._gen_ctrl._associate_with_ticket(runbook_id, ticket_id)
    if success:
        return {"message": f"Runbook {runbook_id} successfully associated with ticket {ticket_id}",
                "runbook_id": runbook_id, "ticket_id": ticket_id, "success": True}
    raise HTTPException(status_code=500, detail=f"Failed to associate runbook {runbook_id} with ticket {ticket_id}.")


@router.get("/demo/{runbook_id}/debug")
async def debug_runbook_meta_data(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debug endpoint to inspect runbook meta_data and ticket associations."""
    import json
    from app.models.runbook import Runbook
    runbook = db.query(Runbook).filter(
        Runbook.id == runbook_id, Runbook.tenant_id == current_user.tenant_id
    ).first()
    if not runbook:
        raise HTTPException(status_code=404, detail=f"Runbook {runbook_id} not found")
    meta_data = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else (runbook.meta_data or {})
    return {
        "runbook_id": runbook.id, "runbook_title": runbook.title,
        "status": runbook.status, "is_active": runbook.is_active,
        "meta_data": meta_data, "meta_data_type": type(runbook.meta_data).__name__,
        "ticket_id_in_meta": meta_data.get("ticket_id"), "meta_data_raw": runbook.meta_data,
    }


@router.post("/demo/cleanup-orphaned-references")
async def cleanup_orphaned_runbook_references(db: Session = Depends(get_db)):
    """Clean up orphaned runbook references from tickets."""
    try:
        return RunbookController(db, tenant_id=1).cleanup_orphaned_runbook_references()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up orphaned references: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup orphaned references: {str(e)}")
