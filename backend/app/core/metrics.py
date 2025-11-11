"""Prometheus metrics helpers for orchestrator and worker instrumentation."""

from __future__ import annotations

from prometheus_client import Counter, Histogram


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


def record_connector_result(connector: str, status: str) -> None:
    connector_command_total.labels(connector=connector, status=status).inc()


def observe_connector_latency(connector: str, duration_seconds: float) -> None:
    connector_command_latency_seconds.labels(connector=connector).observe(
        max(duration_seconds, 0.0)
    )


def record_connector_retry(connector: str, reason: str) -> None:
    connector_retry_total.labels(connector=connector, reason=reason or "unknown").inc()


