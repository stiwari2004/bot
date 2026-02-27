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
    def normalize_opmanager_alert(opm_alarm: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OpManager alarm to internal alert format.
        
        Example alarm (from listAlarms):
        {
            "severity":"<img ...>Critical",
            "numericSeverity":1,
            "deviceType":"-",
            "severityString":"Critical",
            "statusStr":"Critical",
            "displayName":"System",
            "eventType":"SelfMonitoring Alarm",
            "message":"OpManager Disk Free Space is 1GB, configured threshold is 5GB",
            "deviceName":"System",
            "statusNum":1,
            "modTimeLong":1772036296205,
            "modTime":"25 Feb 2026 04:18:16 PM UTC",
            "alarmId":"1",
            "category":"SelfMonitoring",
            "entity":"8_FREE_SPACE",
            "alarmcode":"SM_THRESHOLD_DOWN_DiskSpaceMonitor",
            "status":1,
            "who":"Unacknowledged"
        }
        """
        try:
            # Map numeric severity (1 Critical, 2 Trouble, 3 Attention, 4 Service Down, 5 Clear)
            numeric = opm_alarm.get("numericSeverity")
            severity_map = {
                1: "critical",
                2: "high",
                3: "medium",
                4: "high",
                5: "low",
            }
            severity = severity_map.get(numeric, "medium")

            # StatusNum / status: 1 Critical, 2 Trouble, 3 Attention, 4 Service Down, 5 Clear
            status_num = opm_alarm.get("statusNum") or opm_alarm.get("status")
            status = "firing"
            if status_num in [5]:
                status = "resolved"

            external_id = str(opm_alarm.get("alarmId") or opm_alarm.get("alarmcode") or "")
            title = opm_alarm.get("message") or opm_alarm.get("alarmcode") or "OpManager Alarm"
            description = opm_alarm.get("message", "")

            entity_type = opm_alarm.get("category", "")
            entity_name = opm_alarm.get("deviceName") or opm_alarm.get("displayName", "")
            entity_id = opm_alarm.get("entity", "")

            triggered_at = None
            if "_parsed_mod_time" in opm_alarm:
                parsed = opm_alarm["_parsed_mod_time"]
                if isinstance(parsed, datetime):
                    triggered_at = parsed

            normalized = {
                "external_id": external_id,
                "title": title,
                "description": description,
                "severity": severity,
                "status": status,
                "source": "opmanager",
                "source_entity_type": entity_type,
                "source_entity_name": entity_name,
                "source_entity_id": entity_id,
                "triggered_at": triggered_at,
                "acknowledged_at": None,
                "resolved_at": None if status != "resolved" else triggered_at,
                "metadata": {
                    "opmanager_alarm_id": opm_alarm.get("alarmId"),
                    "numeric_severity": numeric,
                    "severity_string": opm_alarm.get("severityString"),
                    "status_str": opm_alarm.get("statusStr"),
                    "device_name": entity_name,
                    "category": entity_type,
                    "entity": entity_id,
                    "event_type": opm_alarm.get("eventType"),
                    "alarm_code": opm_alarm.get("alarmcode"),
                    "raw_alarm": opm_alarm,
                },
            }

            return normalized
        except Exception as e:
            logger.error(f"Error normalizing OpManager alarm: {e}", exc_info=True)
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




