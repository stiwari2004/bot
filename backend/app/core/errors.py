"""
Standardized error handling and response formats
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error (400)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(AppException):
    """Resource not found error (404)"""
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} with id {identifier} not found"
        super().__init__(message, status_code=404, details=details)


class UnauthorizedError(AppException):
    """Unauthorized error (401)"""
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class ForbiddenError(AppException):
    """Forbidden error (403)"""
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class ConflictError(AppException):
    """Conflict error (409)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


def create_error_response(
    error: Exception,
    include_details: bool = False,
    user_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error: The exception that occurred
        include_details: Whether to include technical details (for debugging)
        user_message: User-friendly message (if different from error message)
    
    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, AppException):
        status_code = error.status_code
        message = user_message or error.message
        details = error.details if include_details else {}
    elif isinstance(error, HTTPException):
        status_code = error.status_code
        message = user_message or error.detail
        details = {}
    else:
        status_code = 500
        message = user_message or "An internal error occurred"
        details = {"error_type": type(error).__name__} if include_details else {}
    
    response = {
        "error": True,
        "message": message,
        "status_code": status_code
    }
    
    if include_details and details:
        response["details"] = details
    
    return response


def handle_exception(
    error: Exception,
    context: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    include_details: bool = False
) -> HTTPException:
    """
    Handle exception with proper logging and return HTTPException
    
    Args:
        error: The exception that occurred
        context: Context where error occurred (e.g., "analyze_ticket", "create_runbook")
        user_id: Optional user ID for logging
        tenant_id: Optional tenant ID for logging
        include_details: Whether to include technical details in response
    
    Returns:
        HTTPException to raise
    """
    # Log error with context
    log_context = {
        "context": context,
        "error_type": type(error).__name__,
    }
    if user_id:
        log_context["user_id"] = user_id
    if tenant_id:
        log_context["tenant_id"] = tenant_id
    
    if isinstance(error, AppException):
        logger.warning(f"{context}: {error.message}", extra=log_context)
        return HTTPException(
            status_code=error.status_code,
            detail=error.message
        )
    elif isinstance(error, HTTPException):
        logger.warning(f"{context}: {error.detail}", extra=log_context)
        return error
    else:
        # Unexpected error - log with full traceback
        logger.error(
            f"{context}: Unexpected error: {str(error)}",
            exc_info=True,
            extra=log_context
        )
        # Don't expose internal error details to users
        detail = "An internal error occurred. Please try again later."
        if include_details:
            detail = f"{detail} (Error: {type(error).__name__})"
        
        return HTTPException(
            status_code=500,
            detail=detail
        )



