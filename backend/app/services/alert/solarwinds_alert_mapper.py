"""
SolarWinds-specific alert mapping utilities
"""
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class SolarWindsAlertMapper:
    """Maps SolarWinds alert fields to internal alert format"""
    
    SEVERITY_MAP = {
        "Critical": "critical",
        "Error": "high",
        "Warning": "medium",
        "Information": "low",
        "Info": "low"
    }
    
    STATUS_MAP = {
        "Active": "open",
        "Acknowledged": "acknowledged",
        "Resolved": "resolved",
        "Suppressed": "resolved"
    }
    
    @classmethod
    def map_severity(cls, solarwinds_severity: str) -> str:
        """Map SolarWinds severity to internal severity"""
        return cls.SEVERITY_MAP.get(solarwinds_severity, "low")
    
    @classmethod
    def map_status(cls, solarwinds_status: str) -> str:
        """Map SolarWinds status to internal status"""
        return cls.STATUS_MAP.get(solarwinds_status, "open")
    
    @classmethod
    def map_to_internal_alert(cls, solarwinds_alert: Dict[str, Any]) -> Dict[str, Any]:
        """Map SolarWinds alert to internal alert format"""
        return {
            "external_id": str(solarwinds_alert.get("alert_id", "")),
            "title": solarwinds_alert.get("name", "SolarWinds Alert"),
            "description": solarwinds_alert.get("message", ""),
            "severity": cls.map_severity(solarwinds_alert.get("severity", "")),
            "status": cls.map_status(solarwinds_alert.get("state", "")),
            "source": "solarwinds",
            "source_entity_type": solarwinds_alert.get("entity_type", ""),
            "source_entity_name": solarwinds_alert.get("entity_name", ""),
            "source_entity_id": solarwinds_alert.get("entity_id", ""),
            "triggered_at": solarwinds_alert.get("triggered_time"),
            "acknowledged_at": solarwinds_alert.get("acknowledged_time"),
            "resolved_at": solarwinds_alert.get("resolved_time"),
            "metadata": {
                "solarwinds_alert_id": solarwinds_alert.get("alert_id"),
                "custom_properties": solarwinds_alert.get("custom_properties", {})
            }
        }

