"""
Alert normalization service
Converts alerts from various monitoring tools to internal alert format
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertNormalizer:
    """Normalizes alerts from different monitoring tools to internal format"""
    
    @staticmethod
    def normalize_solarwinds_alert(solarwinds_alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize SolarWinds alert to internal alert format
        
        Args:
            solarwinds_alert: SolarWinds alert object (from SolarWindsConnector)
        
        Returns:
            Normalized alert dictionary
        """
        try:
            # Map SolarWinds severity to internal severity
            severity_map = {
                "Critical": "critical",
                "Error": "high",
                "Warning": "medium",
                "Information": "low",
                "Info": "low"
            }
            
            # Map SolarWinds state to internal status
            status_map = {
                "Active": "open",
                "Acknowledged": "acknowledged",
                "Resolved": "resolved"
            }
            
            normalized = {
                "external_id": solarwinds_alert.get("alert_id", ""),
                "title": solarwinds_alert.get("name", "SolarWinds Alert"),
                "description": solarwinds_alert.get("message", ""),
                "severity": severity_map.get(solarwinds_alert.get("severity", ""), "low"),
                "status": status_map.get(solarwinds_alert.get("state", ""), "open"),
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
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing SolarWinds alert: {e}", exc_info=True)
            raise
    
    @staticmethod
    def normalize_datadog_alert(datadog_alert: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Datadog alert to internal format"""
        # Implementation already exists in datadog.py
        # This is a placeholder for consistency
        return datadog_alert
    
    @staticmethod
    def normalize_prometheus_alert(prometheus_alert: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Prometheus alert to internal format"""
        # Implementation already exists in prometheus.py
        # This is a placeholder for consistency
        return prometheus_alert




