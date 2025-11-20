"""
Base controller with common utilities
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseController:
    """Base controller with common request/response utilities"""
    
    @staticmethod
    def handle_error(error: Exception, message: str = "An error occurred") -> HTTPException:
        """Standardized error handling"""
        logger.error(f"{message}: {error}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{message}: {str(error)}"
        )
    
    @staticmethod
    def not_found(resource: str, id: Optional[int] = None) -> HTTPException:
        """Return 404 Not Found error"""
        message = f"{resource} not found"
        if id:
            message += f" (ID: {id})"
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )
    
    @staticmethod
    def bad_request(message: str) -> HTTPException:
        """Return 400 Bad Request error"""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> HTTPException:
        """Return 401 Unauthorized error"""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )
    
    @staticmethod
    def validate_tenant_access(db: Session, tenant_id: int, resource_id: int, model_class) -> bool:
        """Validate that resource belongs to tenant"""
        resource = db.query(model_class).filter(
            model_class.id == resource_id,
            model_class.tenant_id == tenant_id
        ).first()
        return resource is not None




