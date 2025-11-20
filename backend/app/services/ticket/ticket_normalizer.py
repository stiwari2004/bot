"""
Service for normalizing ticket data from various sources
"""
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketNormalizer:
    """Service for normalizing ticket data from various monitoring sources"""
    
    @staticmethod
    def normalize(payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Normalize ticket data from various sources"""
        normalized = {
            "external_id": None,
            "title": "",
            "description": "",
            "severity": "medium",
            "environment": "prod",
            "service": None,
            "metadata": {}
        }
        
        if source == "prometheus":
            normalized["title"] = payload.get("groupLabels", {}).get("alertname", "Alert")
            normalized["description"] = payload.get("annotations", {}).get("description", "")
            normalized["severity"] = payload.get("labels", {}).get("severity", "medium")
            normalized["external_id"] = payload.get("fingerprint")
        
        elif source == "datadog":
            normalized["title"] = payload.get("title", "Datadog Alert")
            normalized["description"] = payload.get("text", "")
            normalized["severity"] = payload.get("priority", "normal")
            normalized["external_id"] = payload.get("id")
        
        elif source == "pagerduty":
            normalized["title"] = payload.get("summary", "PagerDuty Incident")
            normalized["description"] = payload.get("description", "")
            normalized["severity"] = payload.get("urgency", "medium")
            normalized["external_id"] = payload.get("id")
        
        else:
            # Generic format
            normalized["title"] = payload.get("title", payload.get("summary", "Alert"))
            normalized["description"] = payload.get("description", payload.get("body", ""))
            normalized["severity"] = payload.get("severity", payload.get("priority", "medium"))
            normalized["external_id"] = payload.get("id", payload.get("external_id"))
        
        normalized["metadata"] = payload
        
        return normalized




