"""
Input sanitization utilities
"""
import re
import html
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


def sanitize_string(value: str, max_length: Optional[int] = None, allow_newlines: bool = False) -> str:
    """
    Sanitize a string input
    
    Args:
        value: String to sanitize
        max_length: Maximum length (truncate if longer)
        allow_newlines: Whether to allow newline characters
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove control characters (except newlines if allowed)
    if allow_newlines:
        # Allow newlines and tabs, remove other control chars
        sanitized = ''.join(c for c in value if ord(c) >= 32 or c in '\n\t')
    else:
        # Remove all control characters
        sanitized = ''.join(c for c in value if ord(c) >= 32)
    
    # Truncate if too long
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.debug(f"String truncated to {max_length} characters")
    
    return sanitized.strip()


def sanitize_for_logging(value: Any, max_length: int = 200) -> str:
    """
    Sanitize value for safe logging (prevents log injection)
    
    Args:
        value: Value to sanitize
        max_length: Maximum length for logged value
    
    Returns:
        Safe string for logging
    """
    if value is None:
        return "None"
    
    # Convert to string
    str_value = str(value)
    
    # Remove control characters and newlines
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str_value)
    
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


def sanitize_html(value: str) -> str:
    """
    Escape HTML characters to prevent XSS
    
    Args:
        value: String that may contain HTML
    
    Returns:
        HTML-escaped string
    """
    return html.escape(value, quote=True)


def sanitize_dict(data: Dict[str, Any], max_string_length: Optional[int] = None) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary values
    
    Args:
        data: Dictionary to sanitize
        max_string_length: Maximum length for string values
    
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        safe_key = sanitize_string(str(key), max_length=100)
        
        # Sanitize value
        if isinstance(value, str):
            safe_value = sanitize_string(value, max_length=max_string_length, allow_newlines=True)
        elif isinstance(value, dict):
            safe_value = sanitize_dict(value, max_string_length)
        elif isinstance(value, list):
            safe_value = sanitize_list(value, max_string_length)
        else:
            safe_value = value
        
        sanitized[safe_key] = safe_value
    
    return sanitized


def sanitize_list(data: List[Any], max_string_length: Optional[int] = None) -> List[Any]:
    """
    Recursively sanitize list values
    
    Args:
        data: List to sanitize
        max_string_length: Maximum length for string values
    
    Returns:
        Sanitized list
    """
    sanitized = []
    for item in data:
        if isinstance(item, str):
            safe_item = sanitize_string(item, max_length=max_string_length, allow_newlines=True)
        elif isinstance(item, dict):
            safe_item = sanitize_dict(item, max_string_length)
        elif isinstance(item, list):
            safe_item = sanitize_list(item, max_string_length)
        else:
            safe_item = item
        
        sanitized.append(safe_item)
    
    return sanitized


def sanitize_user_input(value: Any) -> Any:
    """
    Sanitize user input (general purpose)
    
    Args:
        value: Input value to sanitize
    
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        return sanitize_string(value, allow_newlines=True)
    elif isinstance(value, dict):
        return sanitize_dict(value)
    elif isinstance(value, list):
        return sanitize_list(value)
    else:
        return value



