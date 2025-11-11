"""
Redis Streams helper client for orchestrator/worker messaging.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

from redis import exceptions as redis_exceptions
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisQueueClient:
    """Utility wrapper around Redis Streams for session orchestration."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def publish(
        self,
        stream: str,
        payload: Dict[str, Any],
        maxlen: Optional[int] = None,
        approximate: bool = True,
    ) -> str:
        """Append a message to a stream."""
        message = {"payload": json.dumps(payload, default=str)}
        trim_len = maxlen or settings.REDIS_DEFAULT_MAXLEN
        try:
            return await self.client.xadd(
                stream,
                message,
                maxlen=trim_len,
                approximate=approximate,
            )
        except redis_exceptions.RedisError:
            logger.exception("Failed to publish message to stream %s", stream)
            raise

    async def read_stream(
        self,
        stream: str,
        last_id: str = "0-0",
        count: int = 10,
        block: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Read entries from a stream starting after ``last_id``.

        Returns a list of (message_id, payload) tuples.
        """
        try:
            response = await self.client.xread(
                streams={stream: last_id},
                count=count,
                block=block,
            )
        except redis_exceptions.RedisError:
            logger.exception("Failed to read from stream %s", stream)
            raise

        entries: List[Tuple[str, Dict[str, Any]]] = []
        for _, messages in response:
            for message_id, data in messages:
                payload = data.get("payload")
                if isinstance(payload, str):
                    try:
                        parsed = json.loads(payload)
                    except json.JSONDecodeError:
                        parsed = {"raw": payload}
                else:
                    parsed = payload
                entries.append((message_id, parsed))
        return entries

    async def ensure_consumer_group(
        self,
        stream: str,
        group: str,
        mkstream: bool = True,
    ) -> None:
        """Create a consumer group if it does not already exist."""
        try:
            await self.client.xgroup_create(stream, group, id="0-0", mkstream=mkstream)
        except redis_exceptions.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise

    async def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block: Optional[int] = 5_000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Read messages via consumer group semantics."""
        try:
            response = await self.client.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block,
            )
        except redis_exceptions.RedisError:
            logger.exception(
                "Failed to read consumer group messages stream=%s group=%s",
                stream,
                group,
            )
            raise

        entries: List[Tuple[str, Dict[str, Any]]] = []
        for _, messages in response:
            for message_id, data in messages:
                payload = data.get("payload")
                if isinstance(payload, str):
                    try:
                        parsed = json.loads(payload)
                    except json.JSONDecodeError:
                        parsed = {"raw": payload}
                else:
                    parsed = payload
                entries.append((message_id, parsed))
        return entries

    async def acknowledge(self, stream: str, group: str, message_ids: Iterable[str]) -> int:
        """Acknowledge messages for a consumer group."""
        message_list = list(message_ids)
        if not message_list:
            return 0
        try:
            return await self.client.xack(stream, group, *message_list)
        except redis_exceptions.RedisError:
            logger.exception(
                "Failed to acknowledge messages stream=%s group=%s message_ids=%s",
                stream,
                group,
                message_list,
            )
            raise

    async def delete(self, stream: str, message_ids: Iterable[str]) -> int:
        """Delete messages from a stream."""
        message_list = list(message_ids)
        if not message_list:
            return 0
        try:
            return await self.client.xdel(stream, *message_list)
        except redis_exceptions.RedisError:
            logger.exception("Failed to delete messages stream=%s", stream)
            raise

    async def close(self) -> None:
        """Close the underlying Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None


queue_client = RedisQueueClient()



