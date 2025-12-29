"""
Permission middleware for FastAPI
Provides decorator for permission-based access control
"""
from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.permission_service import PermissionService
from app.core.logging import get_logger

logger = get_logger(__name__)


def require_permission(
    permission_name: str,
    tenant_id: Optional[int] = None
):
    """
    Decorator to require a specific permission for an endpoint
    
    Usage:
        @router.get("/tickets")
        @require_permission("read:tickets")
        async def list_tickets(...):
            ...
    
    Args:
        permission_name: Permission name (e.g., "read:tickets")
        tenant_id: Optional tenant ID for tenant-scoped checks
                   If None, uses current_user.tenant_id
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies
            db: Session = None
            current_user: User = None
            
            # Find db and current_user in kwargs or args
            for key, value in kwargs.items():
                if isinstance(value, Session):
                    db = value
                elif isinstance(value, User):
                    current_user = value
            
            # If not found in kwargs, check if they're dependencies
            if not db:
                db = kwargs.get('db') or next((arg for arg in args if isinstance(arg, Session)), None)
            if not current_user:
                current_user = kwargs.get('current_user') or next((arg for arg in args if isinstance(arg, User)), None)
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not found"
                )
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Determine tenant_id for permission check
            check_tenant_id = tenant_id
            if check_tenant_id is None:
                check_tenant_id = current_user.tenant_id
            
            # Check permission
            has_perm = PermissionService.has_permission(
                db=db,
                user=current_user,
                permission_name=permission_name,
                tenant_id=check_tenant_id
            )
            
            if not has_perm:
                logger.warning(
                    f"User {current_user.email} (ID: {current_user.id}) denied access to {permission_name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission_name}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(*permission_names: str):
    """
    Decorator to require any one of the specified permissions
    
    Usage:
        @router.get("/tickets")
        @require_any_permission("read:tickets", "manage:tenant")
        async def list_tickets(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = None
            current_user: User = None
            
            for key, value in kwargs.items():
                if isinstance(value, Session):
                    db = value
                elif isinstance(value, User):
                    current_user = value
            
            if not db:
                db = kwargs.get('db') or next((arg for arg in args if isinstance(arg, Session)), None)
            if not current_user:
                current_user = kwargs.get('current_user') or next((arg for arg in args if isinstance(arg, User)), None)
            
            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check if user has any of the required permissions
            has_any = False
            for perm_name in permission_names:
                if PermissionService.has_permission(db, current_user, perm_name):
                    has_any = True
                    break
            
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required one of: {', '.join(permission_names)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_all_permissions(*permission_names: str):
    """
    Decorator to require all of the specified permissions
    
    Usage:
        @router.delete("/tickets/{id}")
        @require_all_permissions("delete:tickets", "manage:tenant")
        async def delete_ticket(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = None
            current_user: User = None
            
            for key, value in kwargs.items():
                if isinstance(value, Session):
                    db = value
                elif isinstance(value, User):
                    current_user = value
            
            if not db:
                db = kwargs.get('db') or next((arg for arg in args if isinstance(arg, Session)), None)
            if not current_user:
                current_user = kwargs.get('current_user') or next((arg for arg in args if isinstance(arg, User)), None)
            
            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check if user has all required permissions
            for perm_name in permission_names:
                if not PermissionService.has_permission(db, current_user, perm_name):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {perm_name}"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator



