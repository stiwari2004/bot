"""
Controller for alert endpoints - handles request/response logic for alerts
Alerts come from monitoring tools and are separate from tickets
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone

from app.controllers.base_controller import BaseController
from app.repositories.alert_repository import AlertRepository
from app.models.alert import Alert
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.services.ticket.ticket_normalizer import TicketNormalizer
from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertController(BaseController):
    """Controller for alert operations"""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.alert_repo = AlertRepository(db)
        self.normalizer = TicketNormalizer()
    
    async def receive_webhook(
        self,
        source: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Receive webhook from monitoring tools and store as alert
        
        IMPORTANT: This creates an ALERT, not a TICKET.
        Tickets come from ticketing tools (ServiceNow/ManageEngine) via polling.
        Alerts are used for validation and matching with tickets.
        """
        try:
            # Normalize alert data (using same normalizer, but storing as alert)
            alert_data = self.normalizer.normalize(payload, source)
            
            # Determine alert status from payload
            alert_status = "firing"
            if source == "prometheus":
                alert_status = payload.get("status", "firing")
            elif source == "azure_monitor":
                data = payload.get("data", {})
                essentials = data.get("essentials", {})
                condition = essentials.get("monitorCondition", "Fired")
                alert_status = "firing" if condition == "Fired" else "resolved"
            elif source == "datadog":
                # Datadog uses "alerting" but we use "firing"
                datadog_status = payload.get("alert_status", "alerting")
                if datadog_status == "alerting":
                    alert_status = "firing"
                elif datadog_status in ["resolved", "ok", "ok_no_data"]:
                    alert_status = "resolved"
                else:
                    alert_status = "firing"  # Default to firing for unknown statuses
            elif source == "splunk":
                alert_status = "firing"  # Default for Splunk
            
            # Extract timestamps
            starts_at = None
            ends_at = None
            if source == "prometheus":
                alerts = payload.get("alerts", [])
                if alerts:
                    starts_at_str = alerts[0].get("startsAt")
                    ends_at_str = alerts[0].get("endsAt")
                    if starts_at_str and starts_at_str != "0001-01-01T00:00:00Z":
                        try:
                            starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
                        except:
                            pass
                    if ends_at_str and ends_at_str != "0001-01-01T00:00:00Z":
                        try:
                            ends_at = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))
                        except:
                            pass
            
            # Create alert using repository
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
                received_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Alert created: id={alert.id}, source={source}, status={alert_status}, title={alert.title[:50]}")
            
            return {
                "alert_id": alert.id,
                "status": alert.status,
                "message": "Alert received and stored"
            }
        except Exception as e:
            logger.error(f"Error receiving alert webhook: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to process alert webhook")
    
    def list_alerts(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List alerts with optional filtering"""
        try:
            alerts = self.alert_repo.get_by_tenant(
                tenant_id=self.tenant_id,
                status=status,
                source=source,
                limit=limit
            )
            
            return {
                "alerts": [
                    {
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
                        "matched_ticket_id": alert.matched_ticket_id,
                        "matched_at": alert.matched_at.isoformat() if alert.matched_at else None,
                        "meta_data": alert.meta_data
                    }
                    for alert in alerts
                ],
                "total": len(alerts)
            }
        except Exception as e:
            logger.error(f"Error listing alerts: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to list alerts")
    
    def get_alert(self, alert_id: int) -> Dict[str, Any]:
        """Get alert details"""
        try:
            alert = self.alert_repo.get_by_id_and_tenant(alert_id, self.tenant_id)
            
            if not alert:
                raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
            
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
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "matched_ticket_id": alert.matched_ticket_id,
                "matched_at": alert.matched_at.isoformat() if alert.matched_at else None,
                "raw_payload": alert.raw_payload,
                "meta_data": alert.meta_data
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting alert: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to get alert")
    
    async def update_alert(
        self,
        alert_id: int,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update alert status (resolve, acknowledge, etc.)
        
        Args:
            alert_id: ID of the alert to update
            status: New status (resolved, acknowledged, firing)
            notes: Optional notes about the update
        
        Returns:
            Updated alert data
        """
        try:
            alert = self.alert_repo.get_by_id_and_tenant(alert_id, self.tenant_id)
            
            if not alert:
                raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
            
            # Validate status
            valid_statuses = ["firing", "resolved", "acknowledged"]
            if status and status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            
            # Store old status before updating
            old_status = alert.status if status else None
            
            # Prepare update data
            update_data = {}
            if status:
                update_data["status"] = status
                # Set resolved_at timestamp if resolving
                if status == "resolved":
                    update_data["resolved_at"] = datetime.now(timezone.utc)
                # Clear resolved_at if changing from resolved to something else
                elif alert.resolved_at:
                    update_data["resolved_at"] = None
                logger.info(f"Alert {alert_id} status updated: {old_status} -> {status}")
            
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Add notes to metadata if provided
            if notes:
                meta_data_update = {}
                if not alert.meta_data:
                    meta_data_update["update_notes"] = []
                else:
                    meta_data_update = alert.meta_data.copy()
                    if "update_notes" not in meta_data_update:
                        meta_data_update["update_notes"] = []
                meta_data_update["update_notes"].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": status or alert.status,
                    "notes": notes
                })
                self.alert_repo.update_alert_metadata(alert_id, self.tenant_id, meta_data_update)
            
            # Update alert using repository
            alert = self.alert_repo.update_alert(alert_id, self.tenant_id, **update_data)
            
            # Sync with source monitoring tool if status changed
            # Allow sync even if old_status is None (new alert being updated immediately)
            if status and (old_status is None or status != old_status):
                try:
                    await self._sync_with_monitoring_tool(alert, status, notes)
                except Exception as sync_error:
                    # Don't fail the update if sync fails, but log it
                    logger.warning(f"Failed to sync alert {alert_id} with monitoring tool {alert.source}: {sync_error}")
            
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
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "matched_ticket_id": alert.matched_ticket_id,
                "matched_at": alert.matched_at.isoformat() if alert.matched_at else None,
                "raw_payload": alert.raw_payload,
                "meta_data": alert.meta_data,
                "message": "Alert updated successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating alert: {e}", exc_info=True)
            raise self.handle_error(e, "Failed to update alert")
    
    async def _sync_with_monitoring_tool(
        self,
        alert: Alert,
        status: str,
        notes: Optional[str] = None
    ) -> None:
        """
        Sync alert status update with the source monitoring tool
        
        Args:
            alert: The alert object
            status: New status
            notes: Optional notes
        """
        try:
            # Find monitoring tool connection
            import json
            
            # Use filter_by_tenant from base repository pattern
            # Since we don't have MonitoringToolConnectionRepository yet, use direct query for now
            # TODO: Create MonitoringToolConnectionRepository
            connection = self.db.query(MonitoringToolConnection).filter(
                MonitoringToolConnection.tenant_id == self.tenant_id,
                MonitoringToolConnection.tool_name == alert.source,
                MonitoringToolConnection.is_active == True
            ).first()
            
            if not connection:
                logger.debug(f"No active connection found for monitoring tool: {alert.source}")
                return
            
            # Get connection metadata
            meta_data = {}
            if connection.meta_data:
                try:
                    meta_data = json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else connection.meta_data
                except:
                    pass
            
            # Get connector and update alert in source system
            if alert.source == "prometheus":
                from app.services.monitoring_connectors.prometheus import PrometheusConnector
                connector = PrometheusConnector()
                
                alertmanager_url = connection.api_base_url or meta_data.get("alertmanager_url", "http://localhost:9093")
                fingerprint = alert.external_id or alert.meta_data.get("prometheus_fingerprint") if alert.meta_data else None
                
                if fingerprint:
                    success = await connector.update_alert_status(
                        alert_fingerprint=fingerprint,
                        status=status,
                        alertmanager_url=alertmanager_url,
                        notes=notes
                    )
                    if success:
                        logger.info(f"Successfully synced Prometheus alert {fingerprint} to {status}")
                else:
                    logger.warning(f"Cannot sync Prometheus alert: missing fingerprint")
                    
            elif alert.source == "datadog":
                from app.services.monitoring_connectors.datadog import DatadogConnector
                connector = DatadogConnector()
                
                api_key = connection.api_key or meta_data.get("api_key")
                application_key = connection.application_key or meta_data.get("application_key")
                base_url = connection.api_base_url or meta_data.get("base_url", "https://api.datadoghq.com")
                
                # Prefer monitor_id (for muting monitors) but fall back to alert_id if needed
                monitor_id = None
                alert_id = None
                scope = None
                if alert.meta_data:
                    monitor_id = alert.meta_data.get("datadog_monitor_id")
                    alert_id = alert.meta_data.get("datadog_alert_id")
                    scope = alert.meta_data.get("datadog_scope")
                if not monitor_id:
                    monitor_id = alert.external_id
                
                if api_key and application_key and monitor_id:
                    logger.info(
                        f"Syncing Datadog alert with monitor_id={monitor_id}, "
                        f"alert_id={alert_id}, scope={scope}, status={status}"
                    )
                    success = await connector.update_alert_status(
                        alert_id=str(monitor_id),
                        status=status,
                        api_key=api_key,
                        application_key=application_key,
                        base_url=base_url,
                        notes=notes,
                        scope=scope
                    )
                    if success:
                        logger.info(f"Successfully synced Datadog monitor {monitor_id} to {status}")
                    else:
                        logger.warning(f"Failed to sync Datadog monitor {monitor_id} to {status}")
                else:
                    logger.warning(
                        "Cannot sync Datadog alert: missing credentials or monitor_id "
                        f"(api_key_present={bool(api_key)}, app_key_present={bool(application_key)}, "
                        f"monitor_id={monitor_id}, alert_id={alert_id})"
                    )
                    
            elif alert.source == "azure_monitor":
                from app.services.monitoring_connectors.azure_monitor import AzureMonitorConnector
                connector = AzureMonitorConnector()
                
                # Azure requires subscription ID, resource group, and access token
                subscription_id = meta_data.get("subscription_id")
                resource_group = meta_data.get("resource_group") or alert.environment
                access_token = connection.api_key or meta_data.get("access_token")
                alert_id = alert.external_id or alert.meta_data.get("azure_alert_id") if alert.meta_data else None
                
                if subscription_id and resource_group and access_token and alert_id:
                    success = await connector.update_alert_status(
                        alert_id=str(alert_id),
                        status=status,
                        subscription_id=subscription_id,
                        resource_group=resource_group,
                        access_token=access_token,
                        notes=notes
                    )
                    if success:
                        logger.info(f"Successfully synced Azure Monitor alert {alert_id} to {status}")
                else:
                    logger.warning(f"Cannot sync Azure Monitor alert: missing required configuration")
                    
            elif alert.source == "splunk":
                from app.services.monitoring_connectors.splunk import SplunkConnector
                connector = SplunkConnector()
                
                splunk_url = connection.api_base_url or meta_data.get("splunk_url", "https://localhost:8089")
                username = connection.api_username or meta_data.get("username")
                password = connection.api_password or meta_data.get("password")
                alert_sid = alert.external_id or alert.meta_data.get("splunk_sid") if alert.meta_data else None
                
                if username and password and alert_sid:
                    success = await connector.update_alert_status(
                        alert_sid=str(alert_sid),
                        status=status,
                        splunk_url=splunk_url,
                        username=username,
                        password=password,
                        notes=notes
                    )
                    if success:
                        logger.info(f"Successfully synced Splunk alert {alert_sid} to {status}")
                else:
                    logger.warning(f"Cannot sync Splunk alert: missing credentials or alert_sid")
                    
            elif alert.source == "solarwinds":
                from app.services.monitoring_connectors.solarwinds import SolarWindsConnector
                from app.services.monitoring_connectors.solarwinds_types import SolarWindsConnectionConfig
                connector = SolarWindsConnector()
                
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
                
                alert_id = alert.external_id or alert.meta_data.get("solarwinds_alert_id") if alert.meta_data else None
                
                if alert_id and config.api_base_url:
                    try:
                        if status == "acknowledged":
                            success = await connector.acknowledge_alert(config, str(alert_id))
                            if success:
                                logger.info(f"Successfully acknowledged SolarWinds alert {alert_id}")
                            else:
                                logger.warning(f"Failed to acknowledge SolarWinds alert {alert_id}")
                        elif status == "resolved":
                            success = await connector.resolve_alert(config, str(alert_id))
                            if success:
                                logger.info(f"Successfully resolved SolarWinds alert {alert_id}")
                            else:
                                logger.warning(f"Failed to resolve SolarWinds alert {alert_id}")
                        else:
                            logger.debug(f"SolarWinds sync: status '{status}' doesn't require action")
                    finally:
                        await connector.close()
                else:
                    logger.warning(
                        f"Cannot sync SolarWinds alert: missing alert_id or api_base_url "
                        f"(alert_id={alert_id}, api_base_url={bool(config.api_base_url)})"
                    )
            else:
                logger.debug(f"No sync implementation for monitoring tool: {alert.source}")
                
        except Exception as e:
            logger.error(f"Error syncing alert with monitoring tool: {e}", exc_info=True)
            # Don't raise - we want the local update to succeed even if sync fails

