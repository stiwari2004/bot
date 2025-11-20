"""
Runbook execution engine with human validation checkpoints
POC version - simplified implementation

NOTE: This file is kept for backward compatibility.
New code should import from app.services.execution instead.
"""
# Backward compatibility - re-export from new structure
from app.services.execution import ExecutionEngine

__all__ = ["ExecutionEngine"]
