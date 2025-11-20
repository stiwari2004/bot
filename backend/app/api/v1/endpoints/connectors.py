"""
Infrastructure Connection Management API
Manage connections to user environments (SSH, databases, APIs, cloud)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.controllers.connector_controller import (
    ConnectorController,
    CredentialCreate,
    InfrastructureConnectionCreate,
    TestCommandRequest
)

router = APIRouter()


@router.post("/credentials")
async def create_credential(
    credential: CredentialCreate,
    db: Session = Depends(get_db)
):
    """Create a new credential"""
    controller = ConnectorController(db)
    return controller.create_credential(credential)


@router.get("/credentials")
async def list_credentials(
    db: Session = Depends(get_db),
    environment: Optional[str] = None
):
    """List all credentials"""
    controller = ConnectorController(db)
    return controller.list_credentials(environment)


@router.post("/infrastructure-connections")
async def create_infrastructure_connection(
    connection: InfrastructureConnectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new infrastructure connection"""
    controller = ConnectorController(db)
    return controller.create_infrastructure_connection(connection)


@router.get("/infrastructure-connections")
async def list_infrastructure_connections(
    db: Session = Depends(get_db),
    connection_type: Optional[str] = None,
    environment: Optional[str] = None
):
    """List all infrastructure connections"""
    controller = ConnectorController(db)
    return controller.list_infrastructure_connections(environment, connection_type)


@router.put("/infrastructure-connections/{connection_id}")
async def update_infrastructure_connection(
    connection_id: int,
    connection: InfrastructureConnectionCreate,
    db: Session = Depends(get_db)
):
    """Update an existing infrastructure connection"""
    controller = ConnectorController(db)
    return controller.update_infrastructure_connection(connection_id, connection)


@router.delete("/infrastructure-connections/{connection_id}")
async def delete_infrastructure_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Delete an infrastructure connection (soft delete by setting is_active=False)"""
    controller = ConnectorController(db)
    return controller.delete_infrastructure_connection(connection_id)


@router.post("/infrastructure-connections/{connection_id}/test")
async def test_infrastructure_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Test infrastructure connection by validating credentials and connectivity"""
    controller = ConnectorController(db)
    return controller.test_connection(connection_id)


@router.get("/infrastructure-connections/{connection_id}/discover")
async def discover_cloud_resources(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Discover resources (VMs, instances) from a cloud account connection"""
    controller = ConnectorController(db)
    return await controller.discover_cloud_resources(connection_id)


@router.post("/infrastructure-connections/{connection_id}/test-command")
async def test_command_on_vm(
    connection_id: int,
    request: TestCommandRequest,
    db: Session = Depends(get_db)
):
    """
    Execute a test command on an Azure VM via Run Command API.
    
    This endpoint allows direct command execution for testing purposes.
    """
    controller = ConnectorController(db)
    return await controller.test_command_on_vm(connection_id, request)


@router.get("/connectors/monitoring")
async def list_monitoring_connectors(db: Session = Depends(get_db)):
    """List available monitoring tool connectors"""
    controller = ConnectorController(db)
    return controller.list_monitoring_connectors()


@router.get("/connectors/ticketing")
async def list_ticketing_connectors(db: Session = Depends(get_db)):
    """List available ticketing tool connectors"""
    controller = ConnectorController(db)
    return controller.list_ticketing_connectors()

