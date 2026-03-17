"""
Mixin: infrastructure connection CRUD and cloud discovery operations
"""
import json
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorInfrastructureMixin:
    """Infrastructure connection operations for ConnectorController."""

    def create_infrastructure_connection(self, connection) -> Dict[str, Any]:
        """Create a new infrastructure connection"""
        try:
            from app.services.subscription.subscription_tracker import SubscriptionTracker
            allowed, error_msg = SubscriptionTracker(self.db).check_node_limit(self.tenant_id)
            if not allowed:
                raise self.bad_request(error_msg or "Node limit reached")

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
                is_active=True,
            )
            return {
                "id": infra_conn.id,
                "name": infra_conn.name,
                "type": infra_conn.connection_type,
                "target_host": infra_conn.target_host,
                "target_port": infra_conn.target_port,
                "message": "Infrastructure connection created successfully",
            }
        except Exception as e:
            logger.error(f"Error creating infrastructure connection: {e}")
            raise self.handle_error(e, "Failed to create infrastructure connection")

    def list_infrastructure_connections(
        self,
        environment: Optional[str] = None,
        connection_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all infrastructure connections"""
        try:
            connections = self.infrastructure_repo.get_by_tenant(self.tenant_id, environment)
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
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in connections
                ]
            }
        except Exception as e:
            logger.error(f"Error listing infrastructure connections: {e}")
            raise self.handle_error(e, "Failed to list infrastructure connections")

    def update_infrastructure_connection(self, connection_id: int, connection) -> Dict[str, Any]:
        """Update an infrastructure connection"""
        try:
            infra_conn = self.infrastructure_repo.get_by_id_and_tenant(connection_id, self.tenant_id)
            if not infra_conn:
                raise self.not_found("Infrastructure connection", connection_id)

            update_data = {
                "name": connection.name,
                "connection_type": connection.connection_type,
                "credential_id": connection.credential_id,
                "target_host": connection.target_host,
                "target_port": connection.target_port,
                "target_service": connection.target_service,
                "environment": connection.environment,
            }
            if connection.meta_data is not None:
                update_data["meta_data"] = json.dumps(connection.meta_data)

            infra_conn = self.infrastructure_repo.update_connection(
                connection_id=connection_id, tenant_id=self.tenant_id, **update_data
            )
            if not infra_conn:
                raise self.not_found("Infrastructure connection", connection_id)

            return {
                "id": infra_conn.id,
                "name": infra_conn.name,
                "type": infra_conn.connection_type,
                "message": "Infrastructure connection updated successfully",
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

            self.infrastructure_repo.update_connection(
                connection_id=connection_id, tenant_id=self.tenant_id, is_active=False
            )
            return {"message": "Infrastructure connection deleted successfully"}
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
        self, connection_id: int, resource_ids: List[str], environment: str = "prod"
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

    async def test_command_on_vm(self, connection_id: int, request) -> Dict[str, Any]:
        """Execute test command on VM"""
        try:
            return await self.connector_service.test_command_on_vm(
                self.db,
                connection_id,
                request.vm_resource_id,
                request.command,
                request.shell,
                self.tenant_id,
            )
        except ValueError as e:
            raise self.bad_request(str(e))
        except Exception as e:
            logger.error(f"Error executing test command: {e}")
            raise self.handle_error(e, "Failed to execute command")
