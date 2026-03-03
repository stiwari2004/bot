"""
Alert Poller Service
Background service that polls monitoring tools for new alerts
Similar to ticketing poller but for monitoring tools
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.models.alert import Alert
from app.services.monitoring_connectors.solarwinds import SolarWindsConnector
from app.services.monitoring_connectors.solarwinds_types import SolarWindsConnectionConfig
from app.services.monitoring_connectors.opmanager import OpManagerConnector
from app.services.alert.alert_normalizer import AlertNormalizer
from app.core.logging import get_logger

logger = get_logger(__name__)


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert datetime/date to ISO string so dicts can be stored in JSON columns."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat") and callable(getattr(obj, "isoformat")):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_serializable(v) for v in obj]
    return obj


class AlertPoller:
    """Background service for polling monitoring tools for alerts"""
    
    def __init__(self):
        self.solarwinds_connector = SolarWindsConnector()
        self.opmanager_connector = OpManagerConnector()
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the alert polling service"""
        if self.running:
            logger.warning("Alert poller service is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Alert poller service started")
    
    async def stop(self):
        """Stop the alert polling service"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Alert poller task did not cancel in time")
            except asyncio.CancelledError:
                pass
        await self.solarwinds_connector.close()
        await self.opmanager_connector.close()
        logger.info("Alert poller service stopped")
    
    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                await self._poll_all_connections()
            except asyncio.CancelledError:
                logger.info("Alert poller loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in alert poller loop: {e}", exc_info=True)
            
            # Wait before next poll cycle (default: 5 minutes)
            try:
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                break
    
    async def _poll_all_connections(self):
        """Poll all active monitoring tool connections"""
        db = SessionLocal()
        try:
            # Get all active API polling connections
            connections = db.query(MonitoringToolConnection).filter(
                MonitoringToolConnection.is_active == True,
                MonitoringToolConnection.connection_type == "api"
            ).all()
            
            logger.info(f"Polling {len(connections)} monitoring tool connections")
            
            for connection in connections:
                try:
                    await self._poll_connection(connection, db)
                except Exception as e:
                    logger.error(f"Error polling connection {connection.id} ({connection.tool_name}): {e}", exc_info=True)
                    connection.last_sync_status = "error"
                    connection.last_error = str(e)[:500]
                    db.commit()
        finally:
            db.close()
    
    async def _poll_connection(self, connection: MonitoringToolConnection, db: Session):
        """Poll a single monitoring tool connection"""
        logger.info(f"Polling {connection.tool_name} connection {connection.id}")
        
        try:
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
            
            if connection.tool_name == "solarwinds":
                await self._poll_solarwinds(connection, meta_data, db)
            elif connection.tool_name == "opmanager":
                await self._poll_opmanager(connection, meta_data, db)
            else:
                logger.warning(f"Alert polling not implemented for {connection.tool_name}")
        except Exception as e:
            logger.error(f"Error polling {connection.tool_name} connection {connection.id}: {e}", exc_info=True)
            connection.last_sync_status = "error"
            connection.last_error = str(e)[:500]
            db.commit()
            raise
    
    async def _poll_solarwinds(
        self,
        connection: MonitoringToolConnection,
        meta_data: Dict[str, Any],
        db: Session
    ):
        """Poll SolarWinds for alerts"""
        try:
            # Build connection config
            config = SolarWindsConnectionConfig(
                api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                username=meta_data.get("username") or connection.api_username,
                password=meta_data.get("password") or connection.api_password,
                api_key=meta_data.get("api_key") or connection.api_key,
                oauth_client_id=meta_data.get("client_id"),
                oauth_client_secret=meta_data.get("client_secret"),
                oauth_token=meta_data.get("oauth_token"),
            )
            
            # Fetch alerts (Active and Acknowledged states)
            alerts = await self.solarwinds_connector.fetch_alerts(
                config=config,
                status_filter=["Active", "Acknowledged"],
                severity_filter=None,  # Fetch all severities
                limit=100
            )
            
            logger.info(f"Fetched {len(alerts)} alerts from SolarWinds connection {connection.id}")
            
            created_count = 0
            updated_count = 0
            
            for solarwinds_alert in alerts:
                # Normalize alert
                normalized = AlertNormalizer.normalize_solarwinds_alert({
                    "alert_id": solarwinds_alert.alert_id,
                    "name": solarwinds_alert.name,
                    "message": solarwinds_alert.message,
                    "severity": solarwinds_alert.severity,
                    "state": solarwinds_alert.state,
                    "entity_type": solarwinds_alert.entity_type,
                    "entity_name": solarwinds_alert.entity_name,
                    "entity_id": solarwinds_alert.entity_id,
                    "triggered_time": solarwinds_alert.triggered_time,
                    "acknowledged_time": solarwinds_alert.acknowledged_time,
                    "resolved_time": solarwinds_alert.resolved_time,
                    "custom_properties": solarwinds_alert.custom_properties or {}
                })
                
                # Check if alert already exists
                existing = db.query(Alert).filter(
                    Alert.tenant_id == connection.tenant_id,
                    Alert.external_id == normalized["external_id"],
                    Alert.source == "solarwinds"
                ).first()
                
                if existing:
                    # Update existing alert
                    existing.title = normalized["title"]
                    existing.description = normalized["description"]
                    existing.severity = normalized["severity"]
                    existing.status = normalized["status"]
                    existing.meta_data = normalized["metadata"]
                    if normalized.get("resolved_at"):
                        existing.resolved_at = normalized["resolved_at"]
                    updated_count += 1
                else:
                    # Create new alert
                    alert = Alert(
                        tenant_id=connection.tenant_id,
                        external_id=normalized["external_id"],
                        source="solarwinds",
                        title=normalized["title"],
                        description=normalized["description"],
                        severity=normalized["severity"],
                        status=normalized["status"],
                        environment="prod",  # Default, can be extracted from metadata
                        service=normalized.get("source_entity_name", ""),
                        starts_at=normalized.get("triggered_at"),
                        resolved_at=normalized.get("resolved_at"),
                        meta_data=normalized["metadata"],
                        raw_payload=normalized
                    )
                    db.add(alert)
                    created_count += 1
            
            # Update connection sync status
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "success"
            connection.last_error = None
            db.commit()
            
            logger.info(
                f"Polled SolarWinds connection {connection.id}: "
                f"{created_count} created, {updated_count} updated"
            )
            
        except Exception as e:
            logger.error(f"Error polling SolarWinds connection {connection.id}: {e}", exc_info=True)
            connection.last_sync_status = "error"
            connection.last_error = str(e)[:500]
            db.commit()
            raise

    async def _poll_opmanager(
        self,
        connection: MonitoringToolConnection,
        meta_data: Dict[str, Any],
        db: Session,
    ):
        """Poll ManageEngine OpManager for alarms"""
        try:
            base_url = connection.api_base_url or meta_data.get("api_base_url", "")
            api_key = meta_data.get("api_key") or connection.api_key

            if not base_url or not api_key:
                raise ValueError("OpManager polling requires api_base_url and api_key")

            # Optional filters from metadata
            alert_type = meta_data.get("alert_type", "ActiveAlarms")
            severity_filter = meta_data.get("severity")  # e.g., "1" for Critical
            limit = int(meta_data.get("limit", 100))

            # MSP central: regionID & selCustomerID are mandatory for external APIs.
            region_id = None
            sel_customer_id = None
            if meta_data:
                region_id = str(meta_data.get("regionID", "-1"))
                sel_customer_id = str(meta_data.get("selCustomerID", "-1"))

            alarms = await self.opmanager_connector.fetch_alarms(
                base_url=base_url,
                api_key=api_key,
                alert_type=alert_type,
                severity=severity_filter,
                limit=limit,
                region_id=region_id,
                sel_customer_id=sel_customer_id,
            )

            logger.info(
                f"Fetched {len(alarms)} alarms from OpManager connection {connection.id}"
            )

            created_count = 0
            updated_count = 0

            for alarm in alarms:
                normalized = AlertNormalizer.normalize_opmanager_alert(alarm)

                existing = (
                    db.query(Alert)
                    .filter(
                        Alert.tenant_id == connection.tenant_id,
                        Alert.external_id == normalized["external_id"],
                        Alert.source == "opmanager",
                    )
                    .first()
                )

                # JSON columns must not contain datetime objects
                payload_for_db = _make_json_serializable(normalized)
                meta_for_db = _make_json_serializable(normalized["metadata"])

                if existing:
                    existing.title = normalized["title"]
                    existing.description = normalized["description"]
                    existing.severity = normalized["severity"]
                    existing.status = normalized["status"]
                    existing.meta_data = meta_for_db
                    if normalized.get("resolved_at"):
                        existing.resolved_at = normalized["resolved_at"]
                    updated_count += 1
                else:
                    alert = Alert(
                        tenant_id=connection.tenant_id,
                        external_id=normalized["external_id"],
                        source="opmanager",
                        title=normalized["title"],
                        description=normalized["description"],
                        severity=normalized["severity"],
                        status=normalized["status"],
                        environment="prod",
                        service=normalized.get("source_entity_name", ""),
                        starts_at=normalized.get("triggered_at"),
                        resolved_at=normalized.get("resolved_at"),
                        meta_data=meta_for_db,
                        raw_payload=payload_for_db,
                    )
                    db.add(alert)
                    created_count += 1

            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "success"
            connection.last_error = None
            db.commit()

            logger.info(
                f"Polled OpManager connection {connection.id}: "
                f"{created_count} created, {updated_count} updated"
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error polling OpManager connection {connection.id}: {e}", exc_info=True)
            connection.last_sync_status = "error"
            connection.last_error = str(e)[:500]
            db.commit()
            raise


# Global alert poller instance
alert_poller = AlertPoller()


async def start_poller():
    """Start the alert poller service (for use in main.py)"""
    await alert_poller.start()


async def stop_poller():
    """Stop the alert poller service (for use in main.py)"""
    await alert_poller.stop()

