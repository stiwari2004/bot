"""
Main input extraction service - orchestrates all extractors
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.services.runbook.input_extractors.datadog_extractor import DatadogInputExtractor
from app.services.runbook.input_extractors.servicenow_extractor import ServiceNowInputExtractor
from app.services.runbook.input_extractors.pattern_extractor import PatternInputExtractor
from app.core.logging import get_logger
import yaml

logger = get_logger(__name__)


class RunbookInputExtractor:
    """
    360-degree input extraction with self-learning capabilities.
    
    Flow:
    1. Extract from metadata (Datadog/ServiceNow)
    2. Pattern-based extraction (fallback)
    3. Return extracted + missing inputs for user input
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
            # Extract YAML from markdown code fence if needed
            if isinstance(runbook_spec, str):
                # Try to extract YAML from markdown
                import re
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
        
        # Step 1: Source-specific extraction
        extracted = {}
        confidence = {}
        
        if ticket.source == "datadog":
            extracted.update(self.datadog_extractor.extract(ticket, runbook_spec))
            confidence.update(self.datadog_extractor.get_confidence(extracted))
        elif ticket.source == "servicenow":
            extracted.update(self.servicenow_extractor.extract(ticket, runbook_spec))
            confidence.update(self.servicenow_extractor.get_confidence(extracted))
        
        # Step 2: Pattern-based extraction (fallback for missing inputs)
        pattern_results = self.pattern_extractor.extract(ticket, runbook_spec)
        pattern_confidence = self.pattern_extractor.get_confidence(pattern_results)
        
        for key, value in pattern_results.items():
            if key not in extracted:  # Don't override metadata extraction
                extracted[key] = value
                confidence[key] = pattern_confidence.get(key, 0.6)
        
        # Step 3: Identify missing required inputs
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




