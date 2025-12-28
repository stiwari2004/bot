"""
Role management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User
from app.services.super_admin_auth import get_current_super_admin
from app.services.role_service import RoleService
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class RoleCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tenant_id: Optional[int] = None
    permission_ids: Optional[List[int]] = None


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    is_system_role: bool
    is_custom: bool
    tenant_id: Optional[int]
    is_global: bool
    is_active: bool
    permission_count: int
    created_at: str


class PermissionInfo(BaseModel):
    id: int
    name: str
    action: str
    resource: str
    description: Optional[str]


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: Optional[int] = None,
    include_system: bool = Query(True),
    include_custom: bool = Query(True),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all roles"""
    try:
        roles = RoleService.list_roles(
            db=db,
            tenant_id=tenant_id,
            include_system=include_system,
            include_custom=include_custom,
            is_active=is_active
        )
        
        # Apply pagination
        paginated_roles = roles[skip:skip+limit]
        
        result = []
        for role in paginated_roles:
            permissions = RoleService.get_role_permissions(db, role.id)
            permission_count = len(permissions)
            result.append({
                "id": role.id,
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system_role": role.is_system_role,
                "is_custom": role.is_custom,
                "tenant_id": role.tenant_id,
                "is_global": role.is_global,
                "is_active": role.is_active,
                "permission_count": permission_count,
                "created_at": role.created_at.isoformat() if role.created_at else "",
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {str(e)}")


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get a specific role"""
    try:
        role = RoleService.get_role(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        permission_count = len(RoleService.get_role_permissions(db, role_id))
        
        return {
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "is_custom": role.is_custom,
            "tenant_id": role.tenant_id,
            "is_global": role.is_global,
            "is_active": role.is_active,
            "permission_count": permission_count,
            "created_at": role.created_at.isoformat() if role.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get role: {str(e)}")


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionInfo])
async def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get all permissions for a role"""
    try:
        role = RoleService.get_role(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        permissions = RoleService.get_role_permissions(db, role_id)
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "action": p.action,
                "resource": p.resource,
                "description": p.description,
            }
            for p in permissions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get role permissions: {str(e)}")


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new custom role"""
    try:
        role = RoleService.create_role(
            db=db,
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            tenant_id=role_data.tenant_id,
            permission_ids=role_data.permission_ids
        )
        
        permission_count = len(RoleService.get_role_permissions(db, role.id))
        
        return {
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "is_custom": role.is_custom,
            "tenant_id": role.tenant_id,
            "is_global": role.is_global,
            "is_active": role.is_active,
            "permission_count": permission_count,
            "created_at": role.created_at.isoformat() if role.created_at else "",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create role: {str(e)}")


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a custom role"""
    try:
        role = RoleService.update_role(
            db=db,
            role_id=role_id,
            display_name=role_data.display_name,
            description=role_data.description,
            is_active=role_data.is_active,
            permission_ids=role_data.permission_ids
        )
        
        permission_count = len(RoleService.get_role_permissions(db, role_id))
        
        return {
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "is_custom": role.is_custom,
            "tenant_id": role.tenant_id,
            "is_global": role.is_global,
            "is_active": role.is_active,
            "permission_count": permission_count,
            "created_at": role.created_at.isoformat() if role.created_at else "",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Delete a custom role"""
    try:
        deleted = RoleService.delete_role(db, role_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return {"message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {str(e)}")


@router.post("/roles/initialize")
async def initialize_roles(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Initialize default roles and permissions (idempotent)"""
    try:
        from app.services.permission_service import PermissionService
        PermissionService.initialize_default_roles(db)
        return {"message": "Default roles and permissions initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize roles: {str(e)}")

