"""
Main input extraction service - orchestrates all extractors.
Tool-agnostic: ticket text (title, description) is parsed the same for any source.
"""
import re
import yaml
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.services.runbook.input_extractors.text_extractor import extract_inputs_from_text
from app.services.runbook.input_extractors.datadog_extractor import DatadogInputExtractor
from app.services.runbook.input_extractors.servicenow_extractor import ServiceNowInputExtractor
from app.services.runbook.input_extractors.pattern_extractor import PatternInputExtractor
from app.core.logging import get_logger

logger = get_logger(__name__)


def _ticket_to_combined_text(ticket: Ticket) -> str:
    """Build a single text from ticket title, description, and string meta/raw. Tool-agnostic."""
    parts = [ticket.title or "", ticket.description or ""]
    meta = ticket.meta_data or {}
    raw = ticket.raw_payload or {}
    if isinstance(meta, dict):
        for v in meta.values():
            if isinstance(v, str):
                parts.append(v)
    if isinstance(raw, dict):
        for k in ("short_description", "description", "comments", "title"):
            v = raw.get(k)
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


class RunbookInputExtractor:
    """
    Input extraction for any ticket source (ServiceNow, Zendesk, Jira, ManageEngine, etc.).

    Flow:
    1. Tool-agnostic text extraction from ticket title + description + meta (all sources)
    2. Source-specific structured extraction (ServiceNow CI/custom fields, Datadog tags only)
    3. Pattern fallback for any remaining missing inputs
    """

    def __init__(self):
        self.datadog_extractor = DatadogInputExtractor()
        self.servicenow_extractor = ServiceNowInputExtractor()
        self.pattern_extractor = PatternInputExtractor()
    
    async def extract_inputs(
        self,
        ticket: Ticket,
        runbook: Runbook,
        db: Session
    ) -> Dict[str, Any]:
        """
        Extract all required inputs for a runbook from ticket data.
        
        Args:
            ticket: Ticket object
            runbook: Runbook object
            db: Database session
            
        Returns:
            {
                "extracted": {...},      # Auto-extracted values
                "missing": [...],        # Missing input names
                "confidence": {...},     # Confidence scores per input
                "source": "...",         # Ticket source
                "ticket_id": int         # Ticket ID
            }
        """
        # Parse runbook YAML
        try:
            runbook_spec = yaml.safe_load(runbook.body_md)
            if isinstance(runbook_spec, str):
                yaml_match = re.search(r'```yaml\n(.*?)\n```', runbook_spec, re.DOTALL)
                if yaml_match:
                    runbook_spec = yaml.safe_load(yaml_match.group(1))
                else:
                    runbook_spec = yaml.safe_load(runbook_spec)
        except Exception as e:
            logger.error(f"Failed to parse runbook YAML: {e}")
            return {
                "extracted": {},
                "missing": [],
                "confidence": {},
                "source": ticket.source,
                "ticket_id": ticket.id,
                "error": f"Failed to parse runbook: {str(e)}"
            }
        
        if not isinstance(runbook_spec, dict):
            logger.error("Runbook spec is not a dictionary")
            return {
                "extracted": {},
                "missing": [],
                "confidence": {},
                "source": ticket.source,
                "ticket_id": ticket.id,
                "error": "Invalid runbook format"
            }
        
        extracted = {}
        confidence = {}

        # Step 1: Tool-agnostic text extraction (all sources)
        combined_text = _ticket_to_combined_text(ticket)
        text_extracted = extract_inputs_from_text(combined_text, runbook_spec)
        for key, value in text_extracted.items():
            if value is not None and value != "":
                extracted[key] = value
                confidence[key] = 0.75

        # Step 2: Source-specific structured only (CI, custom fields, tags)
        if ticket.source == "datadog":
            source_extracted = self.datadog_extractor.extract(ticket, runbook_spec)
            for key, value in source_extracted.items():
                if key not in extracted and value:
                    extracted[key] = value
            confidence.update(self.datadog_extractor.get_confidence(extracted))
        elif ticket.source == "servicenow":
            source_extracted = self.servicenow_extractor.extract(ticket, runbook_spec)
            for key, value in source_extracted.items():
                if key not in extracted and value:
                    extracted[key] = value
            confidence.update(self.servicenow_extractor.get_confidence(extracted))

        # Step 3: Pattern fallback for still-missing
        pattern_results = self.pattern_extractor.extract(ticket, runbook_spec)
        pattern_confidence = self.pattern_extractor.get_confidence(pattern_results)
        for key, value in pattern_results.items():
            if key not in extracted and value:
                extracted[key] = value
                confidence[key] = pattern_confidence.get(key, 0.6)

        # Step 4: Identify missing required inputs
        required_inputs = []
        all_inputs = runbook_spec.get("inputs", [])
        if isinstance(all_inputs, list):
            for inp in all_inputs:
                if isinstance(inp, dict):
                    name = inp.get("name")
                    if name and inp.get("required", False):
                        required_inputs.append(name)
        
        missing = [inp for inp in required_inputs if inp not in extracted or not extracted[inp]]
        
        logger.info(
            f"Input extraction complete for ticket {ticket.id}: "
            f"{len(extracted)} extracted, {len(missing)} missing"
        )
        
        return {
            "extracted": extracted,
            "missing": missing,
            "confidence": confidence,
            "source": ticket.source,
            "ticket_id": ticket.id
        }




