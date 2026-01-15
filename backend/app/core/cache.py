"""
Redis caching utilities
"""
from typing import Optional, Any
import json
import hashlib
from redis.asyncio import Redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client (will be initialized on first use)
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    return _redis_client


def cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and arguments
    
    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Cache key string
    """
    # Create a deterministic key from arguments
    key_parts = [prefix]
    
    # Add positional args
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # Hash complex objects
            key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest()[:8])
    
    # Add keyword args (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hashlib.md5(json.dumps(v, sort_keys=True).encode()).hexdigest()[:8]}")
    
    return ":".join(key_parts)


class CacheService:
    """Service for caching data in Redis"""
    
    def __init__(self):
        self._client: Optional[Redis] = None
    
    async def get_client(self) -> Redis:
        """Get Redis client"""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as string if not JSON
                return value
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            client = await self.get_client()
            
            # Serialize value
            if isinstance(value, (str, int, float, bool)):
                serialized = str(value)
            else:
                serialized = json.dumps(value)
            
            await client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern failed for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False


# Global cache service instance
cache_service = CacheService()


def cached(ttl: int = 3600, key_prefix: str = "cache"):
    """
    Decorator to cache function results
    
    Usage:
        @cached(ttl=3600, key_prefix="runbook")
        async def get_runbook(runbook_id: int):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = cache_key(
                f"{key_prefix}:{func.__name__}",
                *args,
                **kwargs
            )
            
            # Try to get from cache
            cached_value = await cache_service.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key_str}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss for {cache_key_str}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_service.set(cache_key_str, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


