"""
Permission management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.permission import Permission
from app.models.user import User
from app.services.super_admin_auth import get_current_super_admin
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class PermissionResponse(BaseModel):
    id: int
    name: str
    action: str
    resource: str
    description: Optional[str]
    is_active: bool


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all permissions"""
    try:
        query = db.query(Permission)
        
        if is_active is not None:
            query = query.filter(Permission.is_active == is_active)
        if action:
            query = query.filter(Permission.action == action)
        if resource:
            query = query.filter(Permission.resource == resource)
        
        permissions = query.offset(skip).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "action": p.action,
                "resource": p.resource,
                "description": p.description,
                "is_active": p.is_active,
            }
            for p in permissions
        ]
    except Exception as e:
        logger.error(f"Error listing permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list permissions: {str(e)}")


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get a specific permission"""
    try:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        
        return {
            "id": permission.id,
            "name": permission.name,
            "action": permission.action,
            "resource": permission.resource,
            "description": permission.description,
            "is_active": permission.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get permission: {str(e)}")


@router.post("/permissions/initialize")
async def initialize_permissions(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Initialize default permissions (idempotent)"""
    try:
        from app.services.permission_service import PermissionService
        PermissionService.initialize_default_permissions(db)
        return {"message": "Default permissions initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize permissions: {str(e)}")



