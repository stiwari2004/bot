"""
License middleware for FastAPI
Provides decorator for license-based feature access control
"""
from functools import wraps
from typing import Callable
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.license_service import LicenseService
from app.core.logging import get_logger

logger = get_logger(__name__)


def require_license_feature(feature_name: str):
    """
    Decorator to require a specific license feature for an endpoint
    
    Usage:
        @router.get("/solarwinds/alerts")
        @require_license_feature("solarwinds")
        async def get_solarwinds_alerts(...):
            ...
    
    Args:
        feature_name: Feature name (e.g., "solarwinds", "rbac_custom_roles")
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
            
            # Check license feature
            has_feature = LicenseService.has_feature(
                db=db,
                tenant_id=current_user.tenant_id,
                feature_name=feature_name
            )
            
            if not has_feature:
                # Get plan name for better error message
                plan = LicenseService.get_license_plan(db, current_user.tenant_id)
                plan_name = plan.plan_name if plan else "your current plan"
                
                logger.warning(
                    f"Tenant {current_user.tenant_id} (user {current_user.email}) "
                    f"denied access to feature: {feature_name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Feature '{feature_name}' is not available in {plan_name}. Please upgrade your subscription."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_license_feature(*feature_names: str):
    """
    Decorator to require any one of the specified license features
    
    Usage:
        @router.get("/integrations")
        @require_any_license_feature("solarwinds", "datadog", "prometheus")
        async def list_integrations(...):
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
            
            # Check if user has any of the required features
            has_any = False
            for feature_name in feature_names:
                if LicenseService.has_feature(db, current_user.tenant_id, feature_name):
                    has_any = True
                    break
            
            if not has_any:
                plan = LicenseService.get_license_plan(db, current_user.tenant_id)
                plan_name = plan.plan_name if plan else "your current plan"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"None of the required features are available in {plan_name}. Please upgrade your subscription."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator




