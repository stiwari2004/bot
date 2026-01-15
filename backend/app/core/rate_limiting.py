"""
Rate limiting utilities with Redis support
"""
from typing import Optional, Callable, Any
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
import time

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
_redis_client = None


def get_limiter() -> Optional[Limiter]:
    """Get the global limiter instance"""
    return _limiter


def set_limiter(limiter: Limiter) -> None:
    """Set the global limiter instance"""
    global _limiter
    _limiter = _limiter or limiter


async def get_redis_for_rate_limiting():
    """Get Redis client for rate limiting"""
    global _redis_client
    if _redis_client is None:
        try:
            from app.core.cache import get_redis_client
            _redis_client = await get_redis_client()
        except Exception:
            return None
    return _redis_client


async def check_redis_rate_limit(
    key: str,
    limit: int,
    window_seconds: int
) -> tuple:
    """
    Check Redis-based rate limit using sliding window algorithm
    
    Args:
        key: Rate limit key (e.g., "rate_limit:user:123:endpoint:/api/v1/runbooks")
        limit: Maximum number of requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
        rate_limit_info contains: remaining, reset_time, limit
    """
    redis = await get_redis_for_rate_limiting()
    if not redis:
        # If Redis is not available, allow the request (graceful degradation)
        return True, {"remaining": limit, "reset_time": None, "limit": limit}
    
    try:
        now = time.time()
        window_start = now - window_seconds
        
        # Use sorted set to track requests in the window
        # Score is timestamp, value is request ID
        pipe = redis.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        current_count = results[1] + 1  # +1 for the request we just added
        
        is_allowed = current_count <= limit
        remaining = max(0, limit - current_count)
        reset_time = int(now + window_seconds)
        
        return is_allowed, {
            "remaining": remaining,
            "reset_time": reset_time,
            "limit": limit
        }
    except Exception as e:
        # If Redis fails, allow the request (graceful degradation)
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Redis rate limit check failed: {e}")
        return True, {"remaining": limit, "reset_time": None, "limit": limit}


def rate_limit(limit: str, use_redis: bool = False):
    """
    Rate limit decorator that gracefully handles when limiter is None
    
    Args:
        limit: Rate limit string (e.g., "100/minute", "10/hour")
        use_redis: If True, use Redis-based rate limiting instead of slowapi
    
    Usage:
        @rate_limit("100/minute")
        async def my_endpoint(...):
            ...
            
        @rate_limit("10/hour", use_redis=True)
        async def my_endpoint(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Parse limit string (e.g., "100/minute" -> 100 requests per 60 seconds)
        limit_parts = limit.split("/")
        if len(limit_parts) != 2:
            return func  # Invalid format, skip rate limiting
        
        try:
            limit_count = int(limit_parts[0])
            period = limit_parts[1].lower()
            
            # Convert period to seconds
            if period in ["second", "sec"]:
                window_seconds = 1
            elif period in ["minute", "min"]:
                window_seconds = 60
            elif period in ["hour", "hr"]:
                window_seconds = 3600
            elif period in ["day"]:
                window_seconds = 86400
            else:
                return func  # Unknown period, skip rate limiting
        except (ValueError, IndexError):
            return func  # Invalid format, skip rate limiting
        
        if use_redis:
            # Redis-based rate limiting
            async def rate_limited_func(*args, **kwargs):
                # Try to get request from kwargs or args
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request:
                    request = kwargs.get("request")
                
                if not request:
                    # Can't rate limit without request, just call the function
                    return await func(*args, **kwargs)
                
                # Generate rate limit key
                # Try to get user ID from current_user if available
                user_id = None
                for arg in args:
                    if hasattr(arg, "id"):
                        user_id = arg.id
                        break
                if not user_id:
                    user_id = kwargs.get("current_user")
                    if hasattr(user_id, "id"):
                        user_id = user_id.id
                
                # Generate key: rate_limit:user:{user_id}:endpoint:{path} or rate_limit:ip:{ip}:endpoint:{path}
                if user_id:
                    key = f"rate_limit:user:{user_id}:endpoint:{request.url.path}"
                else:
                    ip = request.client.host if request.client else "unknown"
                    key = f"rate_limit:ip:{ip}:endpoint:{request.url.path}"
                
                # Check rate limit
                is_allowed, rate_info = await check_redis_rate_limit(
                    key, limit_count, window_seconds
                )
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "limit": limit_count,
                            "period": period,
                            "reset_time": rate_info["reset_time"]
                        },
                        headers={
                            "X-RateLimit-Limit": str(limit_count),
                            "X-RateLimit-Remaining": str(rate_info["remaining"]),
                            "X-RateLimit-Reset": str(rate_info["reset_time"])
                        }
                    )
                
                # Add rate limit headers to response
                response = await func(*args, **kwargs)
                if hasattr(response, "headers"):
                    response.headers["X-RateLimit-Limit"] = str(limit_count)
                    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
                    response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])
                return response
            
            return rate_limited_func
        else:
            # Use slowapi-based rate limiting (existing implementation)
            if not SLOWAPI_AVAILABLE:
                return func  # No rate limiting if slowapi not available
            limiter = get_limiter()
            if limiter:
                try:
                    return limiter.limit(limit)(func)
                except Exception:
                    # If rate limiter fails, just return the function without limiting
                    # This ensures the endpoint still works even if rate limiting has issues
                    return func
            return func  # No rate limiting if limiter not available
    
    return decorator

