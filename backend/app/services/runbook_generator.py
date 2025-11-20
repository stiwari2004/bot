"""
Runbook generation service using RAG pipeline

NOTE: This file is kept for backward compatibility.
New code should import from app.services.runbook.generation instead.
"""
# Backward compatibility - re-export from new structure
from app.services.runbook.generation import RunbookGeneratorService

__all__ = ["RunbookGeneratorService"]
