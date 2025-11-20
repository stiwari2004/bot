"""
Runbook API endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.runbook import RunbookResponse, RunbookUpdate
from app.services.auth import get_current_user
from app.controllers.runbook_controller import RunbookController

router = APIRouter()


## Removed legacy generation endpoint to avoid confusion; use /generate-agent only


@router.post("/generate-agent", response_model=RunbookResponse)
async def generate_agent_runbook(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an agent-ready YAML runbook (atomic, executable)."""
    controller = RunbookController(db, current_user.tenant_id)
    return await controller.generate_agent_runbook(issue_description, service, env, risk)


# Demo endpoints (no authentication required) - MUST come before /{runbook_id} routes!
@router.post("/demo/generate-agent", response_model=RunbookResponse)
async def generate_agent_runbook_demo(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    ticket_id: Optional[int] = Query(None, description="Optional ticket ID to associate runbook with"),
    db: Session = Depends(get_db)
):
    """Generate an agent-ready YAML runbook (demo tenant)."""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return await controller.generate_agent_runbook(issue_description, service, env, risk, ticket_id)


@router.get("/demo", response_model=List[RunbookResponse])
@router.get("/demo/", response_model=List[RunbookResponse])
async def list_runbooks_demo(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List runbooks for demo tenant"""
    try:
        controller = RunbookController(db, tenant_id=1)  # Demo tenant
        result = controller.list_runbooks(skip, limit)
        # Ensure result is a list
        if not isinstance(result, list):
            result = []
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.exception(f"Error in list_runbooks_demo: {e}", exc_info=True)
        # Return empty list instead of crashing
        return []


@router.get("/demo/{runbook_id}", response_model=RunbookResponse)
async def get_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific runbook by ID for demo tenant"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return controller.get_runbook(runbook_id)


@router.delete("/demo/{runbook_id}")
async def delete_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Delete a runbook for demo tenant (soft delete)"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return controller.delete_runbook(runbook_id)


@router.post("/demo/{runbook_id}/approve", response_model=RunbookResponse)
async def approve_runbook_demo(
    runbook_id: int,
    force_approval: bool = False,
    db: Session = Depends(get_db)
):
    """Approve and publish a draft runbook for demo tenant with duplicate detection"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return await controller.approve_runbook(runbook_id, force_approval)


@router.post("/demo/{runbook_id}/reindex")
async def reindex_runbook_demo(
    runbook_id: int,
    db: Session = Depends(get_db)
):
    """Manually reindex an already approved runbook (for fixing missing indexes)"""
    controller = RunbookController(db, tenant_id=1)  # Demo tenant
    return await controller.reindex_runbook(runbook_id)


# Authenticated endpoints
@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List runbooks for the current tenant"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.list_runbooks(skip, limit)


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific runbook by ID"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.get_runbook(runbook_id)


@router.put("/{runbook_id}", response_model=RunbookResponse)
async def update_runbook(
    runbook_id: int,
    runbook_update: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a runbook"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.update_runbook(runbook_id, runbook_update)


@router.delete("/{runbook_id}")
async def delete_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a runbook (soft delete)"""
    controller = RunbookController(db, current_user.tenant_id)
    return controller.delete_runbook(runbook_id)