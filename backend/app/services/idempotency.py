"""
Utilities for idempotency key reservation and tracking.
"""
from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.services.queue_client import queue_client


class IdempotencyManager:
    """Reserve idempotency keys to prevent duplicate processing."""

    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        self._redis = redis_client or queue_client.client
        self._ttl = max(settings.IDEMPOTENCY_TTL_SECONDS, 60)

    @property
    def redis(self) -> Redis:
        return self._redis

    def _key(self, scope: str, value: str) -> str:
        return f"idempotency:{scope}:{value}"

    async def reserve(self, scope: str, key: str) -> Optional[str]:
        """
        Attempt to reserve an idempotency key.

        Returns the existing value (e.g. session id / stream id) if the key was already used,
        otherwise returns None and marks the key as pending.
        """
        redis_key = self._key(scope, key)
        existing = await self.redis.get(redis_key)
        if existing:
            return existing
        was_set = await self.redis.set(
            redis_key,
            "__PENDING__",
            ex=self._ttl,
            nx=True,
        )
        if was_set:
            return None
        # Another writer won the race; fetch stored value
        return await self.redis.get(redis_key)

    async def commit(self, scope: str, key: str, value: str) -> None:
        """Persist the final value for a reserved key."""
        redis_key = self._key(scope, key)
        await self.redis.set(redis_key, value, ex=self._ttl)

    async def release(self, scope: str, key: str) -> None:
        """Release a reservation (e.g. when processing failed)."""
        redis_key = self._key(scope, key)
        await self.redis.delete(redis_key)


idempotency_manager = IdempotencyManager()


