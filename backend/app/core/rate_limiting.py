"""
Rate limiting utilities
"""
from typing import Optional

# Optional import - graceful fallback if slowapi not installed
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    SLOWAPI_AVAILABLE = True
except ImportError:
    Limiter = None  # type: ignore
    get_remote_address = None  # type: ignore
    SLOWAPI_AVAILABLE = False

# Global limiter instance - will be set by main.py
_limiter: Optional[Limiter] = None


def get_limiter() -> Optional[Limiter]:
    """Get the global limiter instance"""
    return _limiter


def set_limiter(limiter: Limiter) -> None:
    """Set the global limiter instance"""
    global _limiter
    _limiter = _limiter or limiter


def rate_limit(limit: str):
    """
    Rate limit decorator that gracefully handles when limiter is None
    
    Usage:
        @rate_limit("100/minute")
        async def my_endpoint(...):
            ...
    """
    def decorator(func):
        if not SLOWAPI_AVAILABLE:
            return func  # No rate limiting if slowapi not available
        limiter = get_limiter()
        if limiter:
            return limiter.limit(limit)(func)
        return func  # No rate limiting if limiter not available
    return decorator

