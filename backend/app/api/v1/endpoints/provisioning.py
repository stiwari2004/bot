"""
Provisioning API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.core.logging import get_logger
from app.controllers.provisioning_controller import get_provisioning_controller

logger = get_logger(__name__)

router = APIRouter()


# Pydantic models for requests/responses
class ProvisionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str  # terraform, cloudformation, aws, azure, gcp
    template_id: Optional[int] = None
    template_content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    region: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


class ProvisionResponse(BaseModel):
    success: bool
    project_id: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class TemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str
    template_type: Optional[str] = None
    template_content: str
    variables_schema: Optional[Dict[str, Any]] = None
    is_public: bool = False


@router.post("/provision", response_model=ProvisionResponse)
async def provision_infrastructure(
    request: ProvisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provision infrastructure using the specified provider"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id, current_user.id)
        return await controller.provision(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error provisioning infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects(
    state: Optional[str] = None,
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List provisioning projects"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id)
        return await controller.list_projects(state=state, provider=provider)
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a provisioning project"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id)
        return await controller.get_project(project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def destroy_infrastructure(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Destroy provisioned infrastructure"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id)
        return await controller.destroy(project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destroying infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates(
    provider: Optional[str] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List infrastructure templates"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id)
        return await controller.list_templates(provider=provider, template_type=template_type)
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(
    request: TemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an infrastructure template"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id, current_user.id)
        return await controller.create_template(request)
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_template(
    provider: str = Body(...),
    template_content: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate an infrastructure template"""
    try:
        controller = get_provisioning_controller(db, current_user.tenant_id)
        return await controller.validate_template(provider=provider, template_content=template_content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
