"""
In-memory agent worker registry and heartbeat tracking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WorkerState:
    worker_id: str
    capabilities: List[str] = field(default_factory=list)
    network_segment: Optional[str] = None
    environment: Optional[str] = None
    max_concurrency: int = 1
    current_load: int = 0
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.last_heartbeat = datetime.now(timezone.utc)

    @property
    def available_slots(self) -> int:
        return max(self.max_concurrency - self.current_load, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "capabilities": self.capabilities,
            "network_segment": self.network_segment,
            "environment": self.environment,
            "max_concurrency": self.max_concurrency,
            "current_load": self.current_load,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata,
        }


class AgentWorkerManager:
    """Lightweight registry for agent workers."""

    def __init__(self, heartbeat_ttl_seconds: int = 60) -> None:
        self._registry: Dict[str, WorkerState] = {}
        self.heartbeat_ttl = timedelta(seconds=heartbeat_ttl_seconds)

    def register_worker(
        self,
        worker_id: str,
        capabilities: Optional[List[str]] = None,
        network_segment: Optional[str] = None,
        environment: Optional[str] = None,
        max_concurrency: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkerState:
        """Register or update a worker record."""
        state = self._registry.get(worker_id)
        if state is None:
            state = WorkerState(
                worker_id=worker_id,
                capabilities=capabilities or [],
                network_segment=network_segment,
                environment=environment,
                max_concurrency=max_concurrency,
                metadata=metadata or {},
            )
            self._registry[worker_id] = state
            logger.info("Registered worker %s", worker_id)
        else:
            state.capabilities = capabilities or state.capabilities
            state.network_segment = network_segment or state.network_segment
            state.environment = environment or state.environment
            state.max_concurrency = max_concurrency or state.max_concurrency
            if metadata:
                state.metadata.update(metadata)
            logger.debug("Updated worker %s", worker_id)
        state.touch()
        return state

    def heartbeat(self, worker_id: str, current_load: Optional[int] = None) -> Optional[WorkerState]:
        """Refresh heartbeat for an existing worker."""
        state = self._registry.get(worker_id)
        if not state:
            logger.warning("Received heartbeat for unknown worker %s", worker_id)
            return None
        if current_load is not None:
            state.current_load = current_load
        state.touch()
        return state

    def get_worker(self, worker_id: str) -> Optional[WorkerState]:
        return self._registry.get(worker_id)

    def list_active_workers(
        self,
        capabilities: Optional[List[str]] = None,
        environment: Optional[str] = None,
        network_segment: Optional[str] = None,
    ) -> List[WorkerState]:
        """Return active workers that match optional filters."""
        self.cleanup_stale_workers()
        workers = list(self._registry.values())

        def matches(state: WorkerState) -> bool:
            if environment and state.environment != environment:
                return False
            if network_segment and state.network_segment != network_segment:
                return False
            if capabilities:
                if not set(capabilities).issubset(set(state.capabilities)):
                    return False
            return True

        return [state for state in workers if matches(state)]

    def cleanup_stale_workers(self) -> None:
        """Remove workers that have not heartbeated within TTL."""
        cutoff = datetime.now(timezone.utc) - self.heartbeat_ttl
        stale_workers = [worker_id for worker_id, state in self._registry.items() if state.last_heartbeat < cutoff]
        for worker_id in stale_workers:
            logger.warning("Removing stale worker %s", worker_id)
            self._registry.pop(worker_id, None)


agent_worker_manager = AgentWorkerManager()



