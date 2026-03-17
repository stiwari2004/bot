"""
SolarWinds Alert Parser — webhook normalization and alert/node result parsing
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.services.monitoring_connectors.solarwinds_types import SolarWindsAlert

logger = get_logger(__name__)


class SolarWindsAlertParser:
    """Parses and normalizes SolarWinds alert payloads from webhooks and API responses"""

    def normalize_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize SolarWinds webhook payload to internal alert format"""
        try:
            alert_id = payload.get("alert_id") or payload.get("id") or payload.get("event_id")
            title = payload.get("alert_name") or payload.get("name") or payload.get("title", "SolarWinds Alert")
            description = payload.get("alert_message") or payload.get("message") or payload.get("description", "")
            alert_status = payload.get("alert_status") or payload.get("status", "triggered")

            severity_map = {"critical": "critical", "error": "high", "warning": "medium", "info": "low", "information": "low"}
            raw_severity = payload.get("severity") or payload.get("level", "warning")
            severity = severity_map.get(raw_severity.lower(), "medium")

            entity_name = payload.get("entity_name") or payload.get("entity")
            entity_type = payload.get("entity_type")
            service = None
            tags = payload.get("tags", [])
            environment = "prod"

            for tag in tags:
                if isinstance(tag, str):
                    if tag.startswith("env:"):
                        environment = tag.split(":", 1)[1]
                    elif tag.startswith("service:"):
                        service = tag.split(":", 1)[1]

            return {
                "external_id": str(alert_id) if alert_id else None,
                "title": title,
                "description": description,
                "severity": severity,
                "environment": environment,
                "service": service or entity_name,
                "status": "open" if alert_status in ["triggered", "active", "firing"] else "resolved",
                "metadata": {
                    "solarwinds_alert_id": alert_id,
                    "solarwinds_alert_status": alert_status,
                    "solarwinds_entity_name": entity_name,
                    "solarwinds_entity_type": entity_type,
                    "solarwinds_metric_name": payload.get("metric_name"),
                    "solarwinds_metric_value": payload.get("metric_value"),
                    "solarwinds_threshold": payload.get("threshold"),
                    "solarwinds_severity": raw_severity,
                    "solarwinds_tags": tags,
                    "solarwinds_url": payload.get("url"),
                    "solarwinds_timestamp": payload.get("timestamp"),
                    "raw_payload": payload,
                },
            }
        except Exception as e:
            logger.error(f"Error normalizing SolarWinds webhook: {e}", exc_info=True)
            return {
                "external_id": payload.get("alert_id") or payload.get("id"),
                "title": payload.get("alert_name") or payload.get("title", "SolarWinds Alert"),
                "description": payload.get("alert_message") or payload.get("message", ""),
                "severity": "medium",
                "environment": "prod",
                "service": None,
                "metadata": {"raw_payload": payload},
            }

    def build_alert_query(
        self,
        status_filter: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
        limit: int = 100,
    ) -> str:
        """Build SWQL query for fetching Orion on-prem alerts"""
        query = """
        SELECT TOP {limit}
            AlertObjectID, AlertName, AlertMessage, Severity, AlertState,
            EntityType, EntityCaption, EntityUri,
            TriggeredDateTime, AcknowledgedDateTime, ResolvedDateTime
        FROM Orion.AlertActive
        WHERE 1=1
        """
        if status_filter:
            query += " AND (" + " OR ".join(f"AlertState = '{s}'" for s in status_filter) + ")"
        if severity_filter:
            query += " AND (" + " OR ".join(f"Severity = '{s}'" for s in severity_filter) + ")"
        query += " ORDER BY TriggeredDateTime DESC"
        if not isinstance(limit, int) or limit < 1 or limit > 10000:
            limit = 100
        return query.format(limit=limit)

    def parse_orion_alert(self, result: Dict[str, Any]) -> Optional[SolarWindsAlert]:
        """Parse SWQL query result (Orion on-prem) into SolarWindsAlert"""
        try:
            return SolarWindsAlert(
                alert_id=str(result.get("AlertObjectID", "")),
                name=result.get("AlertName", "Unknown Alert"),
                message=result.get("AlertMessage", ""),
                severity=self.map_severity(result.get("Severity", "")),
                state=self.map_state(result.get("AlertState", "")),
                entity_type=result.get("EntityType", ""),
                entity_name=result.get("EntityCaption", ""),
                entity_id=result.get("EntityUri", ""),
                triggered_time=self.parse_datetime(result.get("TriggeredDateTime")),
                acknowledged_time=self.parse_datetime(result.get("AcknowledgedDateTime")),
                resolved_time=self.parse_datetime(result.get("ResolvedDateTime")),
                custom_properties={},
            )
        except Exception as e:
            logger.error(f"Error parsing SolarWinds Orion alert: {e}", exc_info=True)
            return None

    def parse_observability_alert(self, result: Dict[str, Any]) -> Optional[SolarWindsAlert]:
        """Parse Observability SaaS alert result into SolarWindsAlert"""
        try:
            alert_id = str(result.get("id") or result.get("alert_id") or result.get("_id", ""))
            if not alert_id:
                return None

            name = result.get("name") or result.get("title") or result.get("alert_name", "Unknown Alert")
            message = result.get("message") or result.get("description") or result.get("alert_message", "")
            severity_raw = result.get("severity") or result.get("level") or result.get("priority", "")
            severity = self.map_severity(str(severity_raw))
            state_raw = result.get("state") or result.get("status") or result.get("alert_state", "active")
            state = self.map_state(str(state_raw))
            entity_type = result.get("entity_type") or result.get("source_type", "")
            entity_name = result.get("entity_name") or result.get("source_name") or result.get("host", "")
            entity_id = result.get("entity_id") or result.get("source_id") or ""
            triggered_time = self.parse_datetime(
                result.get("created_at") or result.get("triggered_at") or result.get("timestamp")
            )

            skip_keys = {
                "id", "alert_id", "_id", "name", "title", "alert_name",
                "message", "description", "alert_message", "severity", "level", "priority",
                "state", "status", "alert_state", "entity_type", "source_type",
                "entity_name", "source_name", "host", "entity_id", "source_id",
                "created_at", "triggered_at", "timestamp", "acknowledged_at", "resolved_at", "closed_at",
            }
            custom_properties = {k: v for k, v in result.items() if k not in skip_keys}

            return SolarWindsAlert(
                alert_id=alert_id,
                name=name,
                message=message,
                severity=severity,
                state=state,
                entity_type=entity_type,
                entity_name=entity_name,
                entity_id=entity_id,
                triggered_time=triggered_time or datetime.now(timezone.utc),
                acknowledged_time=self.parse_datetime(result.get("acknowledged_at")),
                resolved_time=self.parse_datetime(result.get("resolved_at") or result.get("closed_at")),
                custom_properties=custom_properties,
            )
        except Exception as e:
            logger.error(f"Error parsing Observability SaaS alert: {e}", exc_info=True)
            return None

    def map_severity(self, solarwinds_severity: str) -> str:
        return {"Critical": "Critical", "Error": "Error", "Warning": "Warning", "Information": "Info", "Info": "Info"}.get(
            solarwinds_severity, "Info"
        )

    def map_state(self, solarwinds_state: str) -> str:
        return {"Active": "Active", "Acknowledged": "Acknowledged", "Resolved": "Resolved", "Suppressed": "Resolved"}.get(
            solarwinds_state, "Active"
        )

    def parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        if not dt_value:
            return None
        if isinstance(dt_value, str):
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(dt_value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        if isinstance(dt_value, datetime):
            return dt_value.replace(tzinfo=timezone.utc)
        return None
