"""
Input validation utilities
"""
import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string input
    
    Args:
        value: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
        logger.warning(f"String truncated to {max_length} characters")
    
    # Remove control characters except newlines and tabs
    value = ''.join(c for c in value if ord(c) >= 32 or c in '\n\t')
    
    return value


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_sql_safe(value: str) -> bool:
    """
    Check if value contains potentially dangerous SQL patterns
    
    Args:
        value: String to check
        
    Returns:
        True if safe, False if potentially dangerous
    """
    dangerous_patterns = [
        r';\s*(DROP|DELETE|TRUNCATE|ALTER|CREATE)',
        r'UNION\s+SELECT',
        r'EXEC\s*\(',
        r'xp_\w+',
    ]
    
    value_upper = value.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_upper):
            return False
    
    return True


class BaseInputModel(BaseModel):
    """Base model for input validation with common validators"""
    
    class Config:
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True
        # Extra fields not allowed
        extra = "forbid"


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @field_validator('page')
    @classmethod
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v


class SearchParams(BaseModel):
    """Search parameters"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v):
        return sanitize_string(v, max_length=500)


def validate_and_sanitize_input(value: Any, field_type: type, max_length: Optional[int] = None) -> Any:
    """
    Validate and sanitize input based on type
    
    Args:
        value: Input value
        field_type: Expected type
        max_length: Maximum length for strings
        
    Returns:
        Validated and sanitized value
    """
    if field_type == str:
        if not isinstance(value, str):
            value = str(value)
        value = sanitize_string(value, max_length=max_length or 10000)
    elif field_type == int:
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid integer value: {value}")
    elif field_type == float:
        if not isinstance(value, float):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid float value: {value}")
    elif field_type == bool:
        if not isinstance(value, bool):
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes', 'on')
            else:
                value = bool(value)
    
    return value


