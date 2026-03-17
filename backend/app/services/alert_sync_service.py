"""
AlertSyncService — syncs alert status updates back to source monitoring tools
"""
import json
from typing import Optional
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertSyncService:
    """Pushes status changes to the originating monitoring tool."""

    async def sync(self, db: Session, alert: Alert, status: str, notes: Optional[str] = None) -> None:
        """Sync alert status to source monitoring tool. Failures are logged, not raised."""
        try:
            from app.repositories.monitoring_tool_connection_repository import MonitoringToolConnectionRepository
            connection_repo = MonitoringToolConnectionRepository(db)
            connection = connection_repo.get_by_tenant_and_tool(
                tenant_id=alert.tenant_id,
                tool_name=alert.source,
                active_only=True,
            )
            if not connection:
                logger.debug(f"No active connection found for monitoring tool: {alert.source}")
                return

            meta_data = {}
            if connection.meta_data:
                try:
                    meta_data = (
                        json.loads(connection.meta_data)
                        if isinstance(connection.meta_data, str)
                        else connection.meta_data
                    )
                except Exception:
                    pass

            await self._dispatch(alert, status, notes, connection, meta_data)
        except Exception as e:
            logger.error(f"Error syncing alert with monitoring tool: {e}", exc_info=True)

    async def _dispatch(self, alert: Alert, status: str, notes: Optional[str], connection, meta_data: dict) -> None:
        source = alert.source
        if source == "prometheus":
            await self._sync_prometheus(alert, status, notes, connection, meta_data)
        elif source == "datadog":
            await self._sync_datadog(alert, status, notes, connection, meta_data)
        elif source == "azure_monitor":
            await self._sync_azure_monitor(alert, status, notes, connection, meta_data)
        elif source == "splunk":
            await self._sync_splunk(alert, status, notes, connection, meta_data)
        elif source == "solarwinds":
            await self._sync_solarwinds(alert, status, notes, connection, meta_data)
        else:
            logger.debug(f"No sync implementation for monitoring tool: {source}")

    async def _sync_prometheus(self, alert, status, notes, connection, meta_data):
        from app.services.monitoring_connectors.prometheus import PrometheusConnector
        connector = PrometheusConnector()
        alertmanager_url = connection.api_base_url or meta_data.get("alertmanager_url", "http://localhost:9093")
        fingerprint = alert.external_id or (alert.meta_data.get("prometheus_fingerprint") if alert.meta_data else None)
        if fingerprint:
            success = await connector.update_alert_status(
                alert_fingerprint=fingerprint, status=status, alertmanager_url=alertmanager_url, notes=notes
            )
            if success:
                logger.info(f"Successfully synced Prometheus alert {fingerprint} to {status}")
        else:
            logger.warning("Cannot sync Prometheus alert: missing fingerprint")

    async def _sync_datadog(self, alert, status, notes, connection, meta_data):
        from app.services.monitoring_connectors.datadog import DatadogConnector
        connector = DatadogConnector()
        api_key = connection.api_key or meta_data.get("api_key")
        application_key = connection.application_key or meta_data.get("application_key")
        base_url = connection.api_base_url or meta_data.get("base_url", "https://api.datadoghq.com")
        monitor_id, alert_id, scope = None, None, None
        if alert.meta_data:
            monitor_id = alert.meta_data.get("datadog_monitor_id")
            alert_id = alert.meta_data.get("datadog_alert_id")
            scope = alert.meta_data.get("datadog_scope")
        if not monitor_id:
            monitor_id = alert.external_id
        if api_key and application_key and monitor_id:
            logger.info(f"Syncing Datadog alert with monitor_id={monitor_id}, alert_id={alert_id}, scope={scope}, status={status}")
            success = await connector.update_alert_status(
                alert_id=str(monitor_id), status=status, api_key=api_key,
                application_key=application_key, base_url=base_url, notes=notes, scope=scope,
            )
            if success:
                logger.info(f"Successfully synced Datadog monitor {monitor_id} to {status}")
            else:
                logger.warning(f"Failed to sync Datadog monitor {monitor_id} to {status}")
        else:
            logger.warning(
                f"Cannot sync Datadog alert: missing credentials or monitor_id "
                f"(api_key_present={bool(api_key)}, app_key_present={bool(application_key)}, "
                f"monitor_id={monitor_id}, alert_id={alert_id})"
            )

    async def _sync_azure_monitor(self, alert, status, notes, connection, meta_data):
        from app.services.monitoring_connectors.azure_monitor import AzureMonitorConnector
        connector = AzureMonitorConnector()
        subscription_id = meta_data.get("subscription_id")
        resource_group = meta_data.get("resource_group") or alert.environment
        access_token = connection.api_key or meta_data.get("access_token")
        alert_id = alert.external_id or (alert.meta_data.get("azure_alert_id") if alert.meta_data else None)
        if subscription_id and resource_group and access_token and alert_id:
            success = await connector.update_alert_status(
                alert_id=str(alert_id), status=status, subscription_id=subscription_id,
                resource_group=resource_group, access_token=access_token, notes=notes,
            )
            if success:
                logger.info(f"Successfully synced Azure Monitor alert {alert_id} to {status}")
        else:
            logger.warning("Cannot sync Azure Monitor alert: missing required configuration")

    async def _sync_splunk(self, alert, status, notes, connection, meta_data):
        from app.services.monitoring_connectors.splunk import SplunkConnector
        connector = SplunkConnector()
        splunk_url = connection.api_base_url or meta_data.get("splunk_url", "https://localhost:8089")
        username = connection.api_username or meta_data.get("username")
        password = connection.api_password or meta_data.get("password")
        alert_sid = alert.external_id or (alert.meta_data.get("splunk_sid") if alert.meta_data else None)
        if username and password and alert_sid:
            success = await connector.update_alert_status(
                alert_sid=str(alert_sid), status=status, splunk_url=splunk_url,
                username=username, password=password, notes=notes,
            )
            if success:
                logger.info(f"Successfully synced Splunk alert {alert_sid} to {status}")
        else:
            logger.warning("Cannot sync Splunk alert: missing credentials or alert_sid")

    async def _sync_solarwinds(self, alert, status, notes, connection, meta_data):
        from app.services.monitoring_connectors.solarwinds import SolarWindsConnector
        from app.services.monitoring_connectors.solarwinds_types import SolarWindsConnectionConfig
        connector = SolarWindsConnector()
        config = SolarWindsConnectionConfig(
            api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
            username=meta_data.get("username") or connection.api_username,
            password=meta_data.get("password") or connection.api_password,
            api_key=meta_data.get("api_key") or connection.api_key,
            oauth_client_id=meta_data.get("client_id"),
            oauth_client_secret=meta_data.get("client_secret"),
            oauth_token=meta_data.get("oauth_token"),
        )
        alert_id = alert.external_id or (alert.meta_data.get("solarwinds_alert_id") if alert.meta_data else None)
        if alert_id and config.api_base_url:
            try:
                if status == "acknowledged":
                    success = await connector.acknowledge_alert(config, str(alert_id))
                    logger.info(f"{'Successfully acknowledged' if success else 'Failed to acknowledge'} SolarWinds alert {alert_id}")
                elif status == "resolved":
                    success = await connector.resolve_alert(config, str(alert_id))
                    logger.info(f"{'Successfully resolved' if success else 'Failed to resolve'} SolarWinds alert {alert_id}")
                else:
                    logger.debug(f"SolarWinds sync: status '{status}' doesn't require action")
            finally:
                await connector.close()
        else:
            logger.warning(
                f"Cannot sync SolarWinds alert: missing alert_id or api_base_url "
                f"(alert_id={alert_id}, api_base_url={bool(config.api_base_url)})"
            )


_alert_sync_service = AlertSyncService()


def get_alert_sync_service() -> AlertSyncService:
    return _alert_sync_service
