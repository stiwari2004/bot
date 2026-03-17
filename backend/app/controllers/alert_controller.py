"""
Controller for alert endpoints — handles request/response logic for alerts.
Alerts come from monitoring tools and are separate from tickets.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.controllers.base_controller import BaseController
from app.repositories.alert_repository import AlertRepository
from app.models.alert import Alert
from app.services.ticket.ticket_normalizer import TicketNormalizer
from app.services.alert_sync_service import get_alert_sync_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertController(BaseController):
    """Controller for alert operations"""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.alert_repo = AlertRepository(db)
        self.normalizer = TicketNormalizer()
        self.sync_service = get_alert_sync_service()

    async def receive_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Receive webhook from monitoring tools and store as alert."""
        try:
            alert_data = self.normalizer.normalize(payload, source)

            alert_status = self._parse_alert_status(source, payload)
            starts_at, ends_at = self._parse_timestamps(source, payload)

            alert = self.alert_repo.create_alert(
                tenant_id=self.tenant_id,
                source=source,
                external_id=alert_data.get("external_id"),
                title=alert_data.get("title", "Untitled Alert"),
                description=alert_data.get("description", ""),
                severity=alert_data.get("severity", "medium"),
                environment=alert_data.get("environment", "prod"),
                service=alert_data.get("service"),
                status=alert_status,
                raw_payload=payload,
                meta_data=alert_data.get("metadata", {}),
                starts_at=starts_at,
                ends_at=ends_at,
                received_at=datetime.now(timezone.utc),
            )
            logger.info(f"Alert created: id={alert.id}, source={source}, status={alert_status}, title={alert.title[:50]}")
            return {"alert_id": alert.id, "status": alert.status, "message": "Alert received and stored"}
        except Exception as e:
            logger.error(f"Error receiving alert webhook: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to process alert webhook")

    def list_alerts(self, status: Optional[str] = None, source: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        try:
            alerts = self.alert_repo.get_by_tenant(tenant_id=self.tenant_id, status=status, source=source, limit=limit)
            return {
                "alerts": [self._serialize_alert(a) for a in alerts],
                "total": len(alerts),
            }
        except Exception as e:
            logger.error(f"Error listing alerts: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to list alerts")

    def get_alert(self, alert_id: int) -> Dict[str, Any]:
        try:
            alert = self.alert_repo.get_by_id_and_tenant(alert_id, self.tenant_id)
            if not alert:
                raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
            return {**self._serialize_alert(alert), "raw_payload": alert.raw_payload}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting alert: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get alert")

    async def update_alert(self, alert_id: int, status: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        try:
            alert = self.alert_repo.get_by_id_and_tenant(alert_id, self.tenant_id)
            if not alert:
                raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

            valid_statuses = ["firing", "resolved", "acknowledged"]
            if status and status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

            old_status = alert.status if status else None

            update_data: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
            if status:
                update_data["status"] = status
                update_data["resolved_at"] = datetime.now(timezone.utc) if status == "resolved" else None
                logger.info(f"Alert {alert_id} status updated: {old_status} -> {status}")

            if notes:
                meta_copy = (alert.meta_data or {}).copy()
                meta_copy.setdefault("update_notes", []).append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": status or alert.status,
                    "notes": notes,
                })
                self.alert_repo.update_alert_metadata(alert_id, self.tenant_id, meta_copy)

            alert = self.alert_repo.update_alert(alert_id, self.tenant_id, **update_data)

            if status and (old_status is None or status != old_status):
                try:
                    await self.sync_service.sync(self.db, alert, status, notes)
                except Exception as sync_error:
                    logger.warning(f"Failed to sync alert {alert_id} with monitoring tool {alert.source}: {sync_error}")

            return {**self._serialize_alert(alert), "raw_payload": alert.raw_payload, "message": "Alert updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating alert: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to update alert")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _serialize_alert(self, alert: Alert) -> Dict[str, Any]:
        return {
            "id": alert.id,
            "external_id": alert.external_id,
            "source": alert.source,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "environment": alert.environment,
            "service": alert.service,
            "status": alert.status,
            "received_at": alert.received_at.isoformat() if alert.received_at else None,
            "starts_at": alert.starts_at.isoformat() if alert.starts_at else None,
            "ends_at": alert.ends_at.isoformat() if alert.ends_at else None,
            "resolved_at": alert.resolved_at.isoformat() if getattr(alert, "resolved_at", None) else None,
            "matched_ticket_id": alert.matched_ticket_id,
            "matched_at": alert.matched_at.isoformat() if alert.matched_at else None,
            "meta_data": alert.meta_data,
        }

    @staticmethod
    def _parse_alert_status(source: str, payload: Dict[str, Any]) -> str:
        if source == "prometheus":
            return payload.get("status", "firing")
        if source == "azure_monitor":
            condition = payload.get("data", {}).get("essentials", {}).get("monitorCondition", "Fired")
            return "firing" if condition == "Fired" else "resolved"
        if source == "datadog":
            ds = payload.get("alert_status", "alerting")
            return "resolved" if ds in ("resolved", "ok", "ok_no_data") else "firing"
        if source == "solarwinds":
            sw = payload.get("alert_status") or payload.get("status", "triggered")
            return "resolved" if sw in ("resolved", "ok") else "firing"
        return "firing"

    @staticmethod
    def _parse_timestamps(source: str, payload: Dict[str, Any]):
        starts_at, ends_at = None, None
        if source == "prometheus":
            alerts = payload.get("alerts", [])
            if alerts:
                for key, target in [("startsAt", "starts_at"), ("endsAt", "ends_at")]:
                    val = alerts[0].get(key)
                    if val and val != "0001-01-01T00:00:00Z":
                        try:
                            parsed = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            if target == "starts_at":
                                starts_at = parsed
                            else:
                                ends_at = parsed
                        except Exception:
                            pass
        return starts_at, ends_at
