"""Prometheus metrics helpers for orchestrator and worker instrumentation."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


worker_assignments_total = Counter(
    "worker_assignments_total",
    "Total number of worker assignments processed",
    labelnames=("status",),
)

session_state_transitions_total = Counter(
    "session_state_transitions_total",
    "Session state transitions",
    labelnames=("from_state", "to_state"),
)

execution_step_duration_seconds = Histogram(
    "execution_step_duration_seconds",
    "Execution step duration in seconds",
    labelnames=("connector",),
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM tokens consumed",
    labelnames=("tenant", "direction"),
)

llm_budget_remaining_tokens = Gauge(
    "llm_budget_remaining_tokens",
    "Remaining LLM tokens in current budget window",
    labelnames=("tenant",),
)

llm_budget_total_tokens = Gauge(
    "llm_budget_total_tokens",
    "Configured LLM token budget for tenant",
    labelnames=("tenant",),
)

llm_budget_exceeded_total = Counter(
    "llm_budget_exceeded_total",
    "Budget exceedance events for LLM usage",
    labelnames=("tenant",),
)

llm_rate_limited_total = Counter(
    "llm_rate_limited_total",
    "LLM requests rejected due to rate limiting",
    labelnames=("tenant",),
)

connector_command_total = Counter(
    "connector_command_total",
    "Connector command execution results",
    labelnames=("connector", "status"),
)

connector_command_latency_seconds = Histogram(
    "connector_command_latency_seconds",
    "Connector command latency in seconds",
    labelnames=("connector",),
)

connector_retry_total = Counter(
    "connector_retry_total",
    "Connector command retries",
    labelnames=("connector", "reason"),
)


def record_assignment(status: str) -> None:
    worker_assignments_total.labels(status=status).inc()


def record_state_transition(previous: str, new: str) -> None:
    session_state_transitions_total.labels(from_state=previous, to_state=new).inc()


def observe_step_duration(connector: str, duration_seconds: float) -> None:
    execution_step_duration_seconds.labels(connector=connector).observe(
        max(duration_seconds, 0.0)
    )


def record_llm_tokens(tenant: int, direction: str, tokens: int) -> None:
    llm_tokens_total.labels(tenant=str(tenant), direction=direction).inc(max(tokens, 0))


def set_llm_budget_remaining(tenant: int, remaining: int, total: int) -> None:
    tenant_label = str(tenant)
    llm_budget_remaining_tokens.labels(tenant=tenant_label).set(max(remaining, 0))
    llm_budget_total_tokens.labels(tenant=tenant_label).set(max(total, 0))


def record_llm_budget_exceeded(tenant: int) -> None:
    llm_budget_exceeded_total.labels(tenant=str(tenant)).inc()


def record_llm_rate_limited(tenant: int) -> None:
    llm_rate_limited_total.labels(tenant=str(tenant)).inc()


def record_connector_result(connector: str, status: str) -> None:
    connector_command_total.labels(connector=connector, status=status).inc()


def observe_connector_latency(connector: str, duration_seconds: float) -> None:
    connector_command_latency_seconds.labels(connector=connector).observe(
        max(duration_seconds, 0.0)
    )


def record_connector_retry(connector: str, reason: str) -> None:
    connector_retry_total.labels(connector=connector, reason=reason or "unknown").inc()


