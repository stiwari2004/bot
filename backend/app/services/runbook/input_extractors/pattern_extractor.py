"""
Pattern-based input extractor (fallback).
Delegates to tool-agnostic text extractor so all ticket sources use the same logic.
"""
from typing import Dict, Any
from app.models.ticket import Ticket
from app.services.runbook.input_extractors.base_extractor import BaseInputExtractor
from app.services.runbook.input_extractors.text_extractor import extract_inputs_from_text
from app.core.logging import get_logger

logger = get_logger(__name__)


def _ticket_to_text(ticket: Ticket) -> str:
    """Combine ticket title, description, and string meta into one text. Tool-agnostic."""
    parts = [ticket.title or "", ticket.description or ""]
    if ticket.meta_data and isinstance(ticket.meta_data, dict):
        for v in ticket.meta_data.values():
            if isinstance(v, str):
                parts.append(v)
    raw = ticket.raw_payload or {}
    if isinstance(raw, dict):
        for k in ("short_description", "description", "comments", "title"):
            v = raw.get(k)
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


class PatternInputExtractor(BaseInputExtractor):
    """Fallback: extracts from ticket text using the same tool-agnostic logic as step 1."""

    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Uses shared text extractor on combined ticket text (any source)."""
        text = _ticket_to_text(ticket)
        inputs = extract_inputs_from_text(text, runbook_spec)
        logger.info(f"Pattern (fallback) found {len(inputs)} inputs: {list(inputs.keys())}")
        return inputs
    
    def get_confidence(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Return confidence scores for pattern-extracted inputs (lower confidence)"""
        # Pattern matching has lower confidence than metadata extraction
        return {key: 0.6 for key in extracted.keys()}




