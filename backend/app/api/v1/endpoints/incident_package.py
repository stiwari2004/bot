"""
Incident Package API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.controllers.incident_package_controller import IncidentPackageController
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class GeneratePackageRequest(BaseModel):
    """Request model for generating incident package"""
    session_id: Optional[int] = None


@router.post("/demo/incidents/{ticket_id}/generate-package")
async def generate_incident_package(
    ticket_id: int,
    request: GeneratePackageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate incident package for a ticket"""
    try:
        controller = IncidentPackageController(db, current_user.tenant_id)
        result = controller.generate_package(
            ticket_id=ticket_id,
            session_id=request.session_id,
            generated_by=current_user.id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating incident package for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/incidents/{ticket_id}/package")
async def get_incident_package(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get incident package for a ticket"""
    try:
        controller = IncidentPackageController(db, current_user.tenant_id)
        package = controller.get_package(ticket_id=ticket_id)
        return package
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident package for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/incidents/packages")
async def list_incident_packages(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all incident packages"""
    try:
        controller = IncidentPackageController(db, current_user.tenant_id)
        packages = controller.list_packages(limit=limit)
        return packages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing incident packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
