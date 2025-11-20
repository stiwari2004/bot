"""
Execution orchestrator - backward compatibility shim
New code should import from app.services.execution.orchestrator instead.
"""
# Import from new location for backward compatibility
from app.services.execution.orchestrator import (
    ExecutionOrchestrator,
    execution_orchestrator
)

__all__ = ["ExecutionOrchestrator", "execution_orchestrator"]


