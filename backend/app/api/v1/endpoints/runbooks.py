"""
Runbook API endpoints
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.runbook import RunbookCreate, RunbookResponse, RunbookUpdate
from app.services.auth import get_current_user
from app.services.runbook_generator import RunbookGeneratorService
from app.models.runbook import Runbook

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
    try:
        generator = RunbookGeneratorService()
        runbook = await generator.generate_agent_runbook(
            issue_description=issue_description,
            tenant_id=current_user.tenant_id,
            db=db,
            service=service,
            env=env,
            risk=risk
        )
        return runbook
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runbook generation failed: {str(e)}")


@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List runbooks for the current tenant"""
    try:
        runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == current_user.tenant_id,
            Runbook.is_active == "active"
        ).offset(skip).limit(limit).all()
        
        return [
            RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=runbook.confidence,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
            for runbook in runbooks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runbooks: {str(e)}")


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific runbook by ID"""
    try:
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get runbook: {str(e)}")


@router.put("/{runbook_id}", response_model=RunbookResponse)
async def update_runbook(
    runbook_id: int,
    runbook_update: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a runbook"""
    try:
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        # Update fields
        if runbook_update.title is not None:
            runbook.title = runbook_update.title
        if runbook_update.body_md is not None:
            runbook.body_md = runbook_update.body_md
        if runbook_update.confidence is not None:
            runbook.confidence = runbook_update.confidence
        if runbook_update.meta_data is not None:
            runbook.meta_data = json.dumps(runbook_update.meta_data)
        
        db.commit()
        db.refresh(runbook)
        
        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update runbook: {str(e)}")


@router.delete("/{runbook_id}")
async def delete_runbook(
    runbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a runbook (soft delete)"""
    try:
        runbook = db.query(Runbook).filter(
            Runbook.id == runbook_id,
            Runbook.tenant_id == current_user.tenant_id
        ).first()
        
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        
        runbook.is_active = "archived"
        db.commit()
        
        return {"message": "Runbook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete runbook: {str(e)}")


# Demo endpoints (no authentication required)
## Removed legacy demo generation endpoint; use /demo/generate-agent only


@router.post("/demo/generate-agent", response_model=RunbookResponse)
async def generate_agent_runbook_demo(
    issue_description: str,
    service: str = Query(..., description="Service type: server|network|database|web|storage|auto"),
    env: str = Query(..., description="Environment: prod|staging|dev"),
    risk: str = Query(..., description="Risk: low|medium|high"),
    db: Session = Depends(get_db)
):
    """Generate an agent-ready YAML runbook (demo tenant)."""
    try:
        generator = RunbookGeneratorService()
        runbook = await generator.generate_agent_runbook(
            issue_description=issue_description,
            tenant_id=1,
            db=db,
            service=service,
            env=env,
            risk=risk
        )
        return runbook
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runbook generation failed: {str(e)}")


@router.get("/demo/", response_model=List[RunbookResponse])
async def list_runbooks_demo(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List runbooks for demo tenant"""
    try:
        runbooks = db.query(Runbook).filter(
            Runbook.tenant_id == 1,  # Demo tenant
            Runbook.is_active == "active"
        ).offset(skip).limit(limit).all()
        
        return [
            RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=runbook.confidence,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
            for runbook in runbooks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runbooks: {str(e)}")