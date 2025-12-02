"""
Infrastructure Connection Management API
Manage connections to user environments (SSH, databases, APIs, cloud)
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.controllers.connector_controller import (
    ConnectorController,
    CredentialCreate,
    InfrastructureConnectionCreate,
    TestCommandRequest
)
from app.services.infrastructure.excel_importer import InfrastructureConnectionExcelImporter
from app.models.credential import InfrastructureConnection, Credential
from app.core.logging import get_logger

logger = get_logger(__name__)

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


@router.get("/monitoring")
async def list_monitoring_connectors(db: Session = Depends(get_db)):
    """List available monitoring tool connectors"""
    controller = ConnectorController(db)
    return controller.list_monitoring_connectors()


@router.get("/ticketing")
async def list_ticketing_connectors(db: Session = Depends(get_db)):
    """List available ticketing tool connectors"""
    controller = ConnectorController(db)
    return controller.list_ticketing_connectors()


@router.post("/infrastructure-connections/import-excel")
async def import_infrastructure_connections_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk import infrastructure connections from Excel file
    
    Expected columns (case-insensitive):
    - Required: name, target_host (or host, ip, management_ip), connection_type (or device_type)
    - Optional: target_port, environment, username, password, vendor, model, location, network_segment, etc.
    
    For network devices, additional fields can be provided: vendor, model, device_type, location, network_segment, site, serial_number, firmware_version, snmp_community, snmp_version
    """
    tenant_id = 1  # Demo tenant
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Parse Excel
        importer = InfrastructureConnectionExcelImporter()
        connections_data = importer.parse_excel(file_content, file.filename)
        
        # Import connections
        imported = []
        errors = []
        
        for idx, conn_data in enumerate(connections_data, start=1):
            try:
                # Handle credentials if provided in Excel
                credentials = conn_data.pop('_credentials', None)
                credential_id = None
                
                # If username/password in Excel, create credential
                if credentials and credentials.get('username'):
                    # Check if credential already exists
                    existing_cred = db.query(Credential).filter(
                        Credential.tenant_id == tenant_id,
                        Credential.name == f"{conn_data['name']} - Credentials",
                        Credential.credential_type == conn_data.get('connection_type', 'ssh'),
                        Credential.environment == conn_data.get('environment', 'prod')
                    ).first()
                    
                    if existing_cred:
                        credential_id = existing_cred.id
                    else:
                        # Create a credential for this connection
                        credential = Credential(
                            tenant_id=tenant_id,
                            name=f"{conn_data['name']} - Credentials",
                            credential_type=conn_data.get('connection_type', 'ssh'),
                            environment=conn_data.get('environment', 'prod'),
                            username=credentials['username'],
                            encrypted_password=credentials['password'],  # TODO: Encrypt this
                            host=conn_data['target_host'],
                            port=conn_data.get('target_port', 22),
                        )
                        db.add(credential)
                        db.flush()
                        credential_id = credential.id
                
                # Prepare meta_data
                meta_data = conn_data.pop('meta_data', None)
                meta_data_str = None
                if meta_data:
                    import json
                    meta_data_str = json.dumps(meta_data)
                
                # Create connection
                db_connection = InfrastructureConnection(
                    tenant_id=tenant_id,
                    name=conn_data['name'],
                    connection_type=conn_data['connection_type'],
                    target_host=conn_data['target_host'],
                    target_port=conn_data.get('target_port'),
                    target_service=conn_data.get('target_service'),
                    environment=conn_data.get('environment', 'prod'),
                    credential_id=credential_id,
                    meta_data=meta_data_str,
                )
                db.add(db_connection)
                db.flush()
                
                imported.append({
                    "row": idx,
                    "name": conn_data['name'],
                    "host": conn_data['target_host'],
                    "type": conn_data['connection_type'],
                    "id": db_connection.id
                })
                
            except Exception as e:
                errors.append({
                    "row": idx,
                    "name": conn_data.get('name', 'Unknown'),
                    "error": str(e)
                })
                logger.error(f"Error importing connection row {idx}: {e}", exc_info=True)
        
        db.commit()
        
        return {
            "message": f"Import completed: {len(imported)} connections imported, {len(errors)} errors",
            "imported": imported,
            "errors": errors,
            "total": len(connections_data)
        }
        
    except Exception as e:
        logger.error(f"Error importing infrastructure connections from Excel: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to import connections: {str(e)}")

