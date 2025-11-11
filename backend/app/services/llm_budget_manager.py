"""
Budget and rate limiting utilities for LLM usage.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Dict, Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.core import metrics
from app.services.queue_client import queue_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMRateLimitExceeded(Exception):
    """Raised when a tenant exceeds the allowed request rate."""


class LLMBudgetExceeded(Exception):
    """Raised when a tenant exceeds the configured token budget."""


@dataclass
class _LLMPolicy:
    budget_tokens: int
    window_seconds: int
    rate_limit_per_minute: int
    alert_threshold: float
    expires_at: float


class LLMBudgetManager:
    """Track LLM usage per tenant and enforce rate/budget limits."""

    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        self._redis = redis_client or queue_client.client
        self._default_policy = _LLMPolicy(
            budget_tokens=max(0, settings.LLM_BUDGET_DEFAULT_TOKENS),
            window_seconds=max(60, settings.LLM_BUDGET_WINDOW_SECONDS),
            rate_limit_per_minute=max(0, settings.LLM_RATE_LIMIT_PER_MINUTE),
            alert_threshold=min(max(settings.LLM_BUDGET_ALERT_THRESHOLD, 0.0), 1.0),
            expires_at=0.0,
        )
        self._static_budgets: Dict[str, int] = {
            str(key): max(0, value) for key, value in settings.LLM_TENANT_BUDGETS.items()
        }
        self._policy_cache: Dict[int, _LLMPolicy] = {}
        self._cache_ttl = max(30, settings.LLM_POLICY_CACHE_TTL_SECONDS)

    @property
    def redis(self) -> Redis:
        return self._redis

    async def charge_tokens(
        self,
        *,
        tenant_id: int,
        tokens: int,
        direction: str,
    ) -> None:
        """Increment usage counters and enforce limits."""
        if tokens <= 0:
            return

        policy = await self._fetch_policy(tenant_id)
        await self._enforce_rate_limit(tenant_id=tenant_id, policy=policy)
        await self._enforce_budget(
            tenant_id=tenant_id,
            tokens=tokens,
            direction=direction,
            policy=policy,
        )

    async def get_policy(self, tenant_id: int) -> Dict[str, float]:
        """Return the current policy as a plain dictionary."""
        policy = await self._fetch_policy(tenant_id)
        return {
            "budget_tokens": policy.budget_tokens,
            "window_seconds": policy.window_seconds,
            "rate_limit_per_minute": policy.rate_limit_per_minute,
            "alert_threshold": policy.alert_threshold,
        }

    async def set_policy(
        self,
        *,
        tenant_id: int,
        budget_tokens: Optional[int] = None,
        window_seconds: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
        alert_threshold: Optional[float] = None,
    ) -> None:
        """Persist a policy override for a tenant."""
        base = await self.get_policy(tenant_id)
        policy = {
            "budget_tokens": max(0, budget_tokens if budget_tokens is not None else base["budget_tokens"]),
            "window_seconds": max(60, window_seconds if window_seconds is not None else base["window_seconds"]),
            "rate_limit_per_minute": max(0, rate_limit_per_minute if rate_limit_per_minute is not None else base["rate_limit_per_minute"]),
            "alert_threshold": float(alert_threshold if alert_threshold is not None else base["alert_threshold"]),
        }
        key = f"llm:policy:{tenant_id}"
        await self.redis.set(key, json.dumps(policy))
        self._policy_cache.pop(tenant_id, None)
        logger.info(
            "LLM policy updated tenant=%s budget=%s window=%s rate_limit=%s alert_threshold=%.2f",
            tenant_id,
            policy["budget_tokens"],
            policy["window_seconds"],
            policy["rate_limit_per_minute"],
            policy["alert_threshold"],
        )

    async def get_usage(
        self,
        *,
        tenant_id: int,
    ) -> Dict[str, int]:
        """Return current token usage within the active window."""
        policy = await self._fetch_policy(tenant_id)
        if policy.budget_tokens == 0:
            return {"usage_tokens": 0, "window_start": 0}
        window_start = int(time.time() // policy.window_seconds) * policy.window_seconds
        key = f"llm:budget:{tenant_id}:{window_start}"
        usage = await self.redis.get(key)
        return {
            "usage_tokens": int(usage) if usage else 0,
            "window_start": window_start,
        }

    async def _enforce_rate_limit(self, *, tenant_id: int, policy: _LLMPolicy) -> None:
        if policy.rate_limit_per_minute <= 0:
            return

        key = f"llm:rate:{tenant_id}:{int(time.time() // 60)}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)
        if count > policy.rate_limit_per_minute:
            metrics.record_llm_rate_limited(tenant_id)
            raise LLMRateLimitExceeded(
                f"Tenant {tenant_id} exceeded {policy.rate_limit_per_minute} LLM requests per minute."
            )

    async def _enforce_budget(
        self,
        *,
        tenant_id: int,
        tokens: int,
        direction: str,
        policy: _LLMPolicy,
    ) -> None:
        limit = policy.budget_tokens
        window_seconds = policy.window_seconds
        alert_threshold = max(0.0, min(policy.alert_threshold, 1.0))

        window_start = int(time.time() // window_seconds) * window_seconds
        key = f"llm:budget:{tenant_id}:{window_start}"

        usage = await self.redis.incrby(key, tokens)
        ttl = await self.redis.ttl(key)
        if ttl == -1:
            await self.redis.expire(key, window_seconds)

        metrics.record_llm_tokens(tenant_id, direction, tokens)

        if limit == 0:
            metrics.set_llm_budget_remaining(tenant_id, 0, 0)
            return

        remaining = max(limit - usage, 0)
        metrics.set_llm_budget_remaining(tenant_id, remaining, limit)

        if usage > limit:
            await self.redis.decrby(key, tokens)
            metrics.record_llm_budget_exceeded(tenant_id)
            raise LLMBudgetExceeded(
                f"Tenant {tenant_id} exhausted LLM token budget ({limit} tokens)."
            )

        if alert_threshold > 0:
            utilisation = usage / limit
            if utilisation >= alert_threshold:
                logger.warning(
                    "LLM budget utilisation high tenant=%s usage=%s limit=%s utilisation=%.2f",
                    tenant_id,
                    usage,
                    limit,
                    utilisation,
                )

    async def _fetch_policy(self, tenant_id: int) -> _LLMPolicy:
        now = time.time()
        cached = self._policy_cache.get(tenant_id)
        if cached and cached.expires_at > now:
            return cached

        policy = await self._load_policy_override(tenant_id)
        policy.expires_at = now + self._cache_ttl
        self._policy_cache[tenant_id] = policy
        return policy

    async def _load_policy_override(self, tenant_id: int) -> _LLMPolicy:
        key = f"llm:policy:{tenant_id}"
        raw = await self.redis.get(key)
        if raw:
            try:
                data = json.loads(raw)
                return _LLMPolicy(
                    budget_tokens=max(0, int(data.get("budget_tokens", self._default_budget))),
                    window_seconds=max(60, int(data.get("window_seconds", self._default_policy.window_seconds))),
                    rate_limit_per_minute=max(0, int(data.get("rate_limit_per_minute", self._default_policy.rate_limit_per_minute))),
                    alert_threshold=float(data.get("alert_threshold", self._default_policy.alert_threshold)),
                    expires_at=0.0,
                )
            except Exception as exc:
                logger.warning("LLM policy override invalid for tenant=%s: %s", tenant_id, exc)

        static_budget = self._static_budgets.get(str(tenant_id), self._default_policy.budget_tokens)
        return _LLMPolicy(
            budget_tokens=static_budget,
            window_seconds=self._default_policy.window_seconds,
            rate_limit_per_minute=self._default_policy.rate_limit_per_minute,
            alert_threshold=self._default_policy.alert_threshold,
            expires_at=0.0,
        )


def estimate_tokens(text: str) -> int:
    """Rudimentary token estimator (roughly 4 characters per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


budget_manager = LLMBudgetManager()


