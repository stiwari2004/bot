"""
Base class for input extractors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.ticket import Ticket
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseInputExtractor(ABC):
    """Base class for extracting runbook inputs from ticket metadata"""
    
    @abstractmethod
    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract input values from ticket metadata.
        
        Args:
            ticket: Ticket object with metadata
            runbook_spec: Parsed runbook YAML spec with inputs section
            
        Returns:
            Dictionary mapping input names to extracted values
        """
        pass
    
    @abstractmethod
    def get_confidence(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """
        Get confidence scores for extracted inputs.
        
        Args:
            extracted: Dictionary of extracted inputs
            
        Returns:
            Dictionary mapping input names to confidence scores (0.0-1.0)
        """
        pass
    
    def _get_required_inputs(self, runbook_spec: Dict[str, Any]) -> List[str]:
        """Get list of required input names from runbook spec"""
        inputs = runbook_spec.get("inputs", [])
        if not isinstance(inputs, list):
            return []
        
        required = []
        for inp in inputs:
            if isinstance(inp, dict):
                name = inp.get("name")
                if name and inp.get("required", False):
                    required.append(name)
        
        return required
    
    def _get_all_inputs(self, runbook_spec: Dict[str, Any]) -> List[str]:
        """Get list of all input names from runbook spec"""
        inputs = runbook_spec.get("inputs", [])
        if not isinstance(inputs, list):
            return []
        
        return [inp.get("name") for inp in inputs if isinstance(inp, dict) and inp.get("name")]




