"""
Controller for connector endpoints - handles request/response logic
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from pydantic import BaseModel

from app.controllers.base_controller import BaseController
from app.repositories.credential_repository import CredentialRepository
from app.repositories.infrastructure_repository import InfrastructureRepository
from app.services.credential_service import get_credential_service
from app.services.connector.connector_service import ConnectorService
from app.models.credential import Credential, InfrastructureConnection
from app.core.logging import get_logger
import json

logger = get_logger(__name__)


class CredentialCreate(BaseModel):
    name: str
    credential_type: str
    environment: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None
    service_account_key: Optional[str] = None
    project_id: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: Optional[str] = None


class InfrastructureConnectionCreate(BaseModel):
    name: str
    connection_type: str
    credential_id: Optional[int] = None
    target_host: Optional[str] = None
    target_port: Optional[int] = None
    target_service: Optional[str] = None
    environment: str
    meta_data: Optional[Dict[str, Any]] = None


class TestCommandRequest(BaseModel):
    vm_resource_id: str
    command: str
    shell: Optional[str] = None


class ConnectorController(BaseController):
    """Controller for connector operations"""
    
    def __init__(self, db: Session, tenant_id: int = 1):
        """
        Initialize connector controller
        
        Args:
            db: Database session
            tenant_id: Tenant ID (defaults to 1 for backward compatibility, but should be provided)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.credential_repo = CredentialRepository(db)
        self.infrastructure_repo = InfrastructureRepository(db)
        self.connector_service = ConnectorService()
        self.credential_service = get_credential_service()
    
    def create_credential(self, credential: CredentialCreate) -> Dict[str, Any]:
        """Create a new credential"""
        try:
            # Determine which value to encrypt based on credential type
            value_to_encrypt = None
            metadata = {
                "username": credential.username,
                "host": credential.host,
                "port": credential.port,
                "database_name": credential.database_name
            }
            
            if credential.credential_type == "azure":
                if not credential.tenant_id or not credential.client_id or not credential.client_secret:
                    raise self.bad_request("Azure credentials require tenant_id, client_id, and client_secret")
                value_to_encrypt = credential.client_secret
                metadata.update({
                    "tenant_id": credential.tenant_id,
                    "client_id": credential.client_id,
                    "subscription_id": credential.subscription_id
                })
            elif credential.credential_type == "gcp":
                if not credential.service_account_key:
                    raise self.bad_request("GCP credentials require service_account_key")
                value_to_encrypt = credential.service_account_key
                metadata.update({
                    "project_id": credential.project_id
                })
            elif credential.credential_type == "aws":
                if not credential.access_key_id or not credential.secret_access_key:
                    raise self.bad_request("AWS credentials require access_key_id and secret_access_key")
                value_to_encrypt = credential.secret_access_key
                metadata.update({
                    "access_key_id": credential.access_key_id,
                    "region": credential.region
                })
            elif credential.password:
                value_to_encrypt = credential.password
            elif credential.api_key:
                value_to_encrypt = credential.api_key
            
            if not value_to_encrypt:
                raise self.bad_request("Password, API key, or cloud credentials required")
            
            db_credential = self.credential_service.save_credential(
                db=self.db,
                tenant_id=self.tenant_id,
                name=credential.name,
                type=credential.credential_type,
                value=value_to_encrypt,
                metadata=metadata
            )
            
            return {
                "id": db_credential.id,
                "name": db_credential.name,
                "type": db_credential.credential_type,
                "environment": db_credential.environment,
                "message": "Credential created successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating credential: {e}")
            raise self.handle_error(e, "Failed to create credential")
    
    def list_credentials(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """List all credentials"""
        try:
            credentials = self.credential_repo.get_by_tenant(self.tenant_id, environment)
            
            return {
                "credentials": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "type": c.credential_type,
                        "environment": c.environment,
                        "host": c.host,
                        "port": c.port,
                        "database_name": c.database_name,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in credentials
                ]
            }
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            raise self.handle_error(e, "Failed to list credentials")
    
    def create_infrastructure_connection(self, connection: InfrastructureConnectionCreate) -> Dict[str, Any]:
        """Create a new infrastructure connection"""
        try:
            # Check subscription node limit
            from app.services.subscription.subscription_tracker import SubscriptionTracker
            tracker = SubscriptionTracker(self.db)
            allowed, error_msg = tracker.check_node_limit(self.tenant_id)
            if not allowed:
                raise self.bad_request(error_msg or "Node limit reached")
            
            # Create connection using repository
            infra_conn = self.infrastructure_repo.create_connection(
                tenant_id=self.tenant_id,
                credential_id=connection.credential_id,
                name=connection.name,
                connection_type=connection.connection_type,
                target_host=connection.target_host,
                target_port=connection.target_port,
                target_service=connection.target_service,
                environment=connection.environment,
                meta_data=json.dumps(connection.meta_data) if connection.meta_data else None,
                is_active=True
            )
            
            return {
                "id": infra_conn.id,
                "name": infra_conn.name,
                "type": infra_conn.connection_type,
                "target_host": infra_conn.target_host,
                "target_port": infra_conn.target_port,
                "message": "Infrastructure connection created successfully"
            }
        except Exception as e:
            logger.error(f"Error creating infrastructure connection: {e}")
            raise self.handle_error(e, "Failed to create infrastructure connection")
    
    def list_infrastructure_connections(
        self,
        environment: Optional[str] = None,
        connection_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all infrastructure connections"""
        try:
            connections = self.infrastructure_repo.get_by_tenant(self.tenant_id, environment)
            
            # Filter by connection_type if provided
            if connection_type:
                connections = [c for c in connections if c.connection_type == connection_type]
            
            return {
                "connections": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "type": c.connection_type,
                        "target_host": c.target_host,
                        "target_port": c.target_port,
                        "environment": c.environment,
                        "credential_id": c.credential_id,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in connections
                ]
            }
        except Exception as e:
            logger.error(f"Error listing infrastructure connections: {e}")
            raise self.handle_error(e, "Failed to list infrastructure connections")
    
    def update_infrastructure_connection(
        self,
        connection_id: int,
        connection: InfrastructureConnectionCreate
    ) -> Dict[str, Any]:
        """Update an infrastructure connection"""
        try:
            infra_conn = self.infrastructure_repo.get_by_id_and_tenant(connection_id, self.tenant_id)
            if not infra_conn:
                raise self.not_found("Infrastructure connection", connection_id)
            
            # Update connection using repository
            update_data = {
                "name": connection.name,
                "connection_type": connection.connection_type,
                "credential_id": connection.credential_id,
                "target_host": connection.target_host,
                "target_port": connection.target_port,
                "target_service": connection.target_service,
                "environment": connection.environment
            }
            if connection.meta_data is not None:
                update_data["meta_data"] = json.dumps(connection.meta_data)
            
            infra_conn = self.infrastructure_repo.update_connection(
                connection_id=connection_id,
                tenant_id=self.tenant_id,
                **update_data
            )
            if not infra_conn:
                raise self.not_found("Infrastructure connection", connection_id)
            
            return {
                "id": infra_conn.id,
                "name": infra_conn.name,
                "type": infra_conn.connection_type,
                "message": "Infrastructure connection updated successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating infrastructure connection: {e}")
            raise self.handle_error(e, "Failed to update infrastructure connection")
    
    def delete_infrastructure_connection(self, connection_id: int) -> Dict[str, Any]:
        """Delete an infrastructure connection"""
        try:
            infra_conn = self.infrastructure_repo.get_by_id_and_tenant(connection_id, self.tenant_id)
            if not infra_conn:
                raise self.not_found("Infrastructure connection", connection_id)
            
            # Deactivate connection using repository
            self.infrastructure_repo.update_connection(
                connection_id=connection_id,
                tenant_id=self.tenant_id,
                is_active=False
            )
            
            return {
                "message": "Infrastructure connection deleted successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting infrastructure connection: {e}")
            raise self.handle_error(e, "Failed to delete infrastructure connection")
    
    def test_connection(self, connection_id: int) -> Dict[str, Any]:
        """Test infrastructure connection"""
        try:
            return self.connector_service.test_connection(self.db, connection_id, self.tenant_id)
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error testing infrastructure connection: {e}")
            raise self.handle_error(e, "Failed to test connection")
    
    async def discover_cloud_resources(self, connection_id: int) -> Dict[str, Any]:
        """Discover cloud resources"""
        try:
            return await self.connector_service.discover_cloud_resources(
                self.db, connection_id, self.tenant_id
            )
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error discovering cloud resources: {e}")
            raise self.handle_error(e, "Failed to discover resources")
    
    async def save_discovered_resources(
        self,
        connection_id: int,
        resource_ids: List[str],
        environment: str = "prod"
    ) -> Dict[str, Any]:
        """Save discovered resources as InfrastructureConnection entries"""
        try:
            return await self.connector_service.save_discovered_resources(
                self.db, connection_id, self.tenant_id, resource_ids, environment
            )
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error saving discovered resources: {e}")
            raise self.handle_error(e, "Failed to save discovered resources")
    
    async def test_command_on_vm(
        self,
        connection_id: int,
        request: TestCommandRequest
    ) -> Dict[str, Any]:
        """Execute test command on VM"""
        try:
            return await self.connector_service.test_command_on_vm(
                self.db,
                connection_id,
                request.vm_resource_id,
                request.command,
                request.shell,
                self.tenant_id
            )
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error executing test command: {e}")
            raise self.handle_error(e, "Failed to execute command")
    
    def list_monitoring_connectors(self) -> Dict[str, Any]:
        """List available monitoring tool connectors"""
        return {
            "available_connectors": [
                {
                    "type": "datadog",
                    "name": "Datadog",
                    "status": "implemented",
                    "description": "Cloud monitoring and alerting platform",
                    "webhook_supported": True,
                    "api_supported": True
                },
                {
                    "type": "azure_monitor",
                    "name": "Azure Monitor",
                    "status": "implemented",
                    "description": "Microsoft Azure monitoring and alerting service",
                    "webhook_supported": True,
                    "api_supported": False
                },
                {
                    "type": "prometheus",
                    "name": "Prometheus Alertmanager",
                    "status": "implemented",
                    "description": "Open-source monitoring and alerting toolkit",
                    "webhook_supported": True,
                    "api_supported": False
                },
                {
                    "type": "solarwinds",
                    "name": "SolarWinds Orion",
                    "status": "implemented",
                    "description": "Network and infrastructure monitoring platform",
                    "webhook_supported": False,
                    "api_supported": True
                },
                {
                    "type": "splunk",
                    "name": "Splunk",
                    "status": "implemented",
                    "description": "Log aggregation, SIEM, and operational intelligence platform",
                    "webhook_supported": True,
                    "api_supported": True,
                    "hec_supported": True
                },
                {
                    "type": "zabbix",
                    "name": "Zabbix",
                    "status": "planned",
                    "description": "Enterprise monitoring solution"
                },
                {
                    "type": "solarwinds",
                    "name": "SolarWinds Orion",
                    "status": "implemented",
                    "description": "Network and infrastructure monitoring platform",
                    "webhook_supported": False,
                    "api_supported": True
                },
                {
                    "type": "manageengine",
                    "name": "ManageEngine",
                    "status": "planned",
                    "description": "IT management suite"
                }
            ]
        }
    
    def list_ticketing_connectors(self) -> Dict[str, Any]:
        """List available ticketing system connectors"""
        return {
            "available_connectors": [
                {
                    "type": "servicenow",
                    "name": "ServiceNow",
                    "status": "implemented",
                    "description": "IT service management platform"
                },
                {
                    "type": "zendesk",
                    "name": "Zendesk",
                    "status": "planned",
                    "description": "Customer service platform"
                },
                {
                    "type": "manageengine",
                    "name": "ManageEngine ServiceDesk",
                    "status": "planned",
                    "description": "IT service desk solution"
                },
                {
                    "type": "bmcremedy",
                    "name": "BMC Remedy",
                    "status": "planned",
                    "description": "ITSM platform"
                }
            ]
        }

