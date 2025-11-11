"""
Connector Configuration Service
Manages connections to external monitoring and ticketing tools
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from app.core.logging import get_logger
from app.models.credential import Credential, InfrastructureConnection
from app.models.ticket import Ticket
from datetime import datetime
import httpx
import json

logger = get_logger(__name__)


class ConnectorConfig:
    """Configuration for external tool connectors"""
    
    def __init__(self, connector_type: str, config: Dict[str, Any]):
        self.connector_type = connector_type
        self.config = config
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        if self.connector_type == "datadog":
            return {
                "DD-API-KEY": self.config.get("api_key"),
                "DD-APPLICATION-KEY": self.config.get("application_key")
            }
        elif self.connector_type == "servicenow":
            return {
                "Authorization": f"Basic {self.config.get('auth_token')}"
            }
        elif self.connector_type == "zendesk":
            return {
                "Authorization": f"Basic {self.config.get('auth_token')}"
            }
        elif self.connector_type == "prometheus":
            # Prometheus usually doesn't need auth for queries
            return {}
        else:
            return {}


class MonitoringConnector:
    """Base class for monitoring tool connectors"""
    
    async def fetch_alerts(self, config: ConnectorConfig) -> List[Dict[str, Any]]:
        """Fetch alerts from monitoring tool"""
        raise NotImplementedError
    
    async def create_ticket_from_alert(self, alert: Dict[str, Any], config: ConnectorConfig) -> Dict[str, Any]:
        """Convert alert to ticket format"""
        raise NotImplementedError


class DatadogConnector(MonitoringConnector):
    """Connector for Datadog monitoring"""
    
    async def fetch_alerts(self, config: ConnectorConfig) -> List[Dict[str, Any]]:
        """Fetch alerts from Datadog"""
        try:
            base_url = config.config.get("base_url", "https://api.datadoghq.com")
            headers = config.get_auth_headers()
            
            async with httpx.AsyncClient() as client:
                # Fetch active alerts/monitors
                response = await client.get(
                    f"{base_url}/api/v1/monitor",
                    headers=headers,
                    params={"status": "Alert"}
                )
                
                if response.status_code == 200:
                    monitors = response.json()
                    alerts = []
                    for monitor in monitors:
                        alerts.append({
                            "id": monitor.get("id"),
                            "title": monitor.get("name"),
                            "message": monitor.get("message", ""),
                            "severity": "high" if monitor.get("priority") == 1 else "medium",
                            "status": "alert",
                            "created_at": datetime.utcnow().isoformat()
                        })
                    return alerts
                else:
                    logger.error(f"Datadog API error: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching Datadog alerts: {e}")
            return []
    
    async def create_ticket_from_alert(self, alert: Dict[str, Any], config: ConnectorConfig) -> Dict[str, Any]:
        """Convert Datadog alert to ticket format"""
        return {
            "source": "datadog",
            "external_id": str(alert.get("id")),
            "title": alert.get("title", "Datadog Alert"),
            "description": alert.get("message", ""),
            "severity": alert.get("severity", "medium"),
            "environment": "prod",
            "raw_payload": alert
        }


class ServiceNowConnector:
    """Connector for ServiceNow ticketing system"""
    
    async def create_ticket(self, ticket_data: Dict[str, Any], config: ConnectorConfig) -> Dict[str, Any]:
        """Create ticket in ServiceNow"""
        try:
            base_url = config.config.get("base_url")
            headers = config.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            # ServiceNow API format
            snow_ticket = {
                "short_description": ticket_data.get("title"),
                "description": ticket_data.get("description"),
                "urgency": "1" if ticket_data.get("severity") == "high" else "2",
                "impact": "1" if ticket_data.get("severity") == "high" else "2",
                "category": "Infrastructure"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/now/table/incident",
                    headers=headers,
                    json=snow_ticket
                )
                
                if response.status_code in [200, 201]:
                    result = response.json().get("result", {})
                    return {
                        "success": True,
                        "ticket_id": result.get("sys_id"),
                        "ticket_number": result.get("number")
                    }
                else:
                    logger.error(f"ServiceNow API error: {response.status_code}")
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Error creating ServiceNow ticket: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_ticket_status(self, ticket_id: str, status: str, config: ConnectorConfig) -> Dict[str, Any]:
        """Update ticket status in ServiceNow"""
        try:
            base_url = config.config.get("base_url")
            headers = config.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            # Map our status to ServiceNow state
            state_map = {
                "resolved": "6",  # Resolved
                "closed": "7",   # Closed
                "in_progress": "2"  # In Progress
            }
            
            snow_state = state_map.get(status, "2")
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{base_url}/api/now/table/incident/{ticket_id}",
                    headers=headers,
                    json={"state": snow_state}
                )
                
                if response.status_code == 200:
                    return {"success": True}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Error updating ServiceNow ticket: {e}")
            return {"success": False, "error": str(e)}


class ConnectorService:
    """Service for managing external tool connectors"""
    
    def __init__(self):
        self.connectors = {
            "datadog": DatadogConnector(),
            "servicenow": ServiceNowConnector(),
            "prometheus": None,  # Prometheus uses webhooks typically
            "zabbix": None,  # TODO: Implement
            "solarwinds": None,  # TODO: Implement
            "manageengine": None,  # TODO: Implement
            "zendesk": None,  # TODO: Implement
            "bmcremedy": None,  # TODO: Implement
        }
    
    def get_connector_config(self, db: Session, tenant_id: int, connector_type: str) -> Optional[ConnectorConfig]:
        """Get connector configuration from database"""
        connection = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.connection_type == connector_type,
            InfrastructureConnection.is_active == True
        ).first()
        
        if not connection:
            return None
        
        # Get credential if needed
        credential_data = {}
        if connection.credential_id:
            credential = db.query(Credential).filter(Credential.id == connection.credential_id).first()
            if credential:
                from app.services.credential_service import get_credential_service
                cred_service = get_credential_service()
                decrypted = cred_service.get_credential(db, tenant_id, credential.id)
                credential_data["api_key"] = decrypted
                credential_data["auth_token"] = decrypted
        
        # Build config from connection details
        config = {
            "base_url": connection.target_host,
            "port": connection.target_port,
            **credential_data
        }
        
        return ConnectorConfig(connector_type, config)
    
    async def fetch_monitoring_alerts(
        self,
        db: Session,
        tenant_id: int,
        connector_type: str
    ) -> List[Dict[str, Any]]:
        """Fetch alerts from monitoring tool"""
        connector = self.connectors.get(connector_type)
        if not connector:
            logger.warning(f"Connector {connector_type} not implemented")
            return []
        
        config = self.get_connector_config(db, tenant_id, connector_type)
        if not config:
            logger.warning(f"No configuration found for {connector_type}")
            return []
        
        return await connector.fetch_alerts(config)
    
    async def update_ticketing_ticket(
        self,
        db: Session,
        tenant_id: int,
        connector_type: str,
        external_ticket_id: str,
        status: str
    ) -> Dict[str, Any]:
        """Update ticket status in ticketing system"""
        connector = self.connectors.get(connector_type)
        if not connector or not hasattr(connector, 'update_ticket_status'):
            logger.warning(f"Connector {connector_type} does not support ticket updates")
            return {"success": False, "error": "Not supported"}
        
        config = self.get_connector_config(db, tenant_id, connector_type)
        if not config:
            return {"success": False, "error": "No configuration found"}
        
        return await connector.update_ticket_status(external_ticket_id, status, config)


# Global instance
_connector_service: Optional[ConnectorService] = None


def get_connector_service() -> ConnectorService:
    """Get or create connector service instance"""
    global _connector_service
    if _connector_service is None:
        _connector_service = ConnectorService()
    return _connector_service




