"""
Runbook authenticated CRUD, versioning, citations, and input endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiting import rate_limit
from app.models.user import User
from app.schemas.runbook import RunbookResponse, RunbookUpdate
from app.services.auth import get_current_user
from app.controllers.runbook_controller import RunbookController
from app.controllers.runbook_version_controller import RunbookVersionController
from app.controllers.citation_controller import CitationController
from app.api.v1.endpoints.runbooks_schemas import UserInputsRequest

router = APIRouter()


@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List runbooks for the current tenant (cached)"""
    from app.core.cache import cache_service, cache_key
    cache_key_str = cache_key("runbooks:list", current_user.tenant_id, skip, limit)
    cached = await cache_service.get(cache_key_str)
    if cached is not None:
        return [RunbookResponse(**item) if isinstance(item, dict) else item for item in cached]
    try:
        result = RunbookController(db, current_user.tenant_id).list_runbooks(skip, limit)
        cache_data = [item.dict() if hasattr(item, "dict") else item for item in result]
        await cache_service.set(cache_key_str, cache_data, ttl=3600)
        return result
    except Exception as e:
        error_str = str(e).lower()
        if any(k in error_str for k in ("connection", "database", "operational")):
            raise HTTPException(status_code=503, detail="Database connection failed")
        raise


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific runbook by ID (cached)"""
    from app.core.cache import cache_service, cache_key
    cache_key_str = cache_key("runbook:get", runbook_id, current_user.tenant_id)
    cached = await cache_service.get(cache_key_str)
    if cached is not None:
        return RunbookResponse(**cached) if isinstance(cached, dict) else cached
    result = RunbookController(db, current_user.tenant_id).get_runbook(runbook_id)
    cache_data = result.dict() if hasattr(result, "dict") else result
    await cache_service.set(cache_key_str, cache_data, ttl=3600)
    return result


@router.put("/{runbook_id}", response_model=RunbookResponse)
async def update_runbook(
    runbook_id: int,
    runbook_update: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a runbook (invalidates cache)"""
    from app.core.cache import cache_service, cache_key
    result = RunbookController(db, current_user.tenant_id).update_runbook(runbook_id, runbook_update)
    await cache_service.delete(cache_key("runbook:get", runbook_id, current_user.tenant_id))
    await cache_service.delete_pattern(f"runbooks:list:{current_user.tenant_id}:*")
    return result


@router.delete("/{runbook_id}")
async def delete_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a runbook (soft delete, invalidates cache)"""
    from app.core.cache import cache_service, cache_key
    result = RunbookController(db, current_user.tenant_id).delete_runbook(runbook_id)
    await cache_service.delete(cache_key("runbook:get", runbook_id, current_user.tenant_id))
    await cache_service.delete_pattern(f"runbooks:list:{current_user.tenant_id}:*")
    return result


# ── Versioning ────────────────────────────────────────────────────────────────

@router.get("/demo/{runbook_id}/versions")
@rate_limit("60/minute")
async def get_runbook_versions(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await RunbookVersionController(db, current_user.tenant_id).get_version_history(runbook_id)


@router.post("/demo/{runbook_id}/versions")
@rate_limit("30/minute")
async def create_runbook_version(
    runbook_id: int,
    title: Optional[str] = None,
    body_md: Optional[str] = None,
    body_yaml: Optional[str] = None,
    change_summary: Optional[str] = None,
    change_type: str = Query("minor", regex="^(major|minor|patch)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await RunbookVersionController(db, current_user.tenant_id).create_version(
        runbook_id=runbook_id, title=title, body_md=body_md, body_yaml=body_yaml,
        change_summary=change_summary, change_type=change_type, created_by=current_user.id,
    )


@router.get("/demo/{runbook_id}/versions/{version_id_1}/diff/{version_id_2}")
@rate_limit("60/minute")
async def get_version_diff(
    runbook_id: int,
    version_id_1: int,
    version_id_2: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await RunbookVersionController(db, current_user.tenant_id).get_version_diff(
        runbook_id, version_id_1, version_id_2
    )


@router.post("/demo/versions/{version_id}/set-current")
@rate_limit("30/minute")
async def set_current_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await RunbookVersionController(db, current_user.tenant_id).set_current_version(version_id)


# ── Citations ─────────────────────────────────────────────────────────────────

@router.post("/demo/{runbook_id}/citations/verify")
@rate_limit("30/minute")
async def verify_runbook_citations(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CitationController(db, current_user.tenant_id).verify_runbook_citations(runbook_id)


@router.get("/demo/{runbook_id}/citations/health")
@rate_limit("60/minute")
async def get_citation_health(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CitationController(db, current_user.tenant_id).get_citation_health(runbook_id)


@router.post("/demo/citations/{citation_id}/verify")
@rate_limit("30/minute")
async def verify_single_citation(
    citation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CitationController(db, current_user.tenant_id).verify_single_citation(citation_id)


# ── Input extraction & learning ───────────────────────────────────────────────

@router.post("/demo/{runbook_id}/extract-inputs")
@rate_limit("60/minute")
async def extract_inputs(
    runbook_id: int,
    ticket_id: int = Query(..., description="Ticket ID to extract inputs from"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await RunbookController(db, tenant_id=current_user.tenant_id).extract_inputs(ticket_id, runbook_id)


@router.post("/demo/{runbook_id}/learn-inputs")
@rate_limit("30/minute")
async def learn_from_user_input(
    runbook_id: int,
    ticket_id: int = Query(..., description="Ticket ID"),
    user_inputs: UserInputsRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RunbookController(db, tenant_id=current_user.tenant_id).learn_from_user_input(
        ticket_id, runbook_id, user_inputs.inputs
    )


@router.get("/demo/metadata-mappings/flags")
@rate_limit("60/minute")
async def get_mapping_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    min_confidence: float = Query(0.8, description="Minimum confidence threshold"),
):
    return RunbookController(db, tenant_id=current_user.tenant_id).get_mapping_flags(min_confidence)
