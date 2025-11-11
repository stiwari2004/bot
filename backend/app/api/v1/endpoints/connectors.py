"""
Infrastructure Connection Management API
Manage connections to user environments (SSH, databases, APIs, cloud)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.models.credential import Credential, InfrastructureConnection
from app.services.credential_service import get_credential_service
from app.core.logging import get_logger
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter()
logger = get_logger(__name__)


class CredentialCreate(BaseModel):
    name: str
    credential_type: str  # ssh, api_key, database, aws, azure, gcp
    environment: str  # prod, staging, dev
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None


class InfrastructureConnectionCreate(BaseModel):
    name: str
    connection_type: str  # ssh, database, api, cloud
    credential_id: Optional[int] = None
    target_host: Optional[str] = None
    target_port: Optional[int] = None
    target_service: Optional[str] = None
    environment: str  # prod, staging, dev
    meta_data: Optional[Dict[str, Any]] = None


@router.post("/credentials")
async def create_credential(
    credential: CredentialCreate,
    db: Session = Depends(get_db)
):
    """Create a new credential"""
    try:
        tenant_id = 1  # Demo tenant
        
        cred_service = get_credential_service()
        
        # Determine which value to encrypt
        value_to_encrypt = None
        if credential.password:
            value_to_encrypt = credential.password
        elif credential.api_key:
            value_to_encrypt = credential.api_key
        
        if not value_to_encrypt:
            raise HTTPException(status_code=400, detail="Password or API key required")
        
        db_credential = cred_service.save_credential(
            db=db,
            tenant_id=tenant_id,
            name=credential.name,
            type=credential.credential_type,
            value=value_to_encrypt,
            metadata={
                "username": credential.username,
                "host": credential.host,
                "port": credential.port,
                "database_name": credential.database_name
            }
        )
        
        return {
            "id": db_credential.id,
            "name": db_credential.name,
            "type": db_credential.credential_type,
            "environment": db_credential.environment,
            "message": "Credential created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create credential: {str(e)}")


@router.get("/credentials")
async def list_credentials(
    db: Session = Depends(get_db),
    environment: Optional[str] = None
):
    """List all credentials"""
    try:
        tenant_id = 1
        
        query = db.query(Credential).filter(Credential.tenant_id == tenant_id)
        
        if environment:
            query = query.filter(Credential.environment == environment)
        
        credentials = query.all()
        
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
        raise HTTPException(status_code=500, detail=f"Failed to list credentials: {str(e)}")


@router.post("/infrastructure-connections")
async def create_infrastructure_connection(
    connection: InfrastructureConnectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new infrastructure connection"""
    try:
        tenant_id = 1
        
        infra_conn = InfrastructureConnection(
            tenant_id=tenant_id,
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
        
        db.add(infra_conn)
        db.commit()
        db.refresh(infra_conn)
        
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
        raise HTTPException(status_code=500, detail=f"Failed to create connection: {str(e)}")


@router.get("/infrastructure-connections")
async def list_infrastructure_connections(
    db: Session = Depends(get_db),
    connection_type: Optional[str] = None,
    environment: Optional[str] = None
):
    """List all infrastructure connections"""
    try:
        tenant_id = 1
        
        query = db.query(InfrastructureConnection).filter(
            InfrastructureConnection.tenant_id == tenant_id,
            InfrastructureConnection.is_active == True
        )
        
        if connection_type:
            query = query.filter(InfrastructureConnection.connection_type == connection_type)
        
        if environment:
            query = query.filter(InfrastructureConnection.environment == environment)
        
        connections = query.all()
        
        return {
            "connections": [
                {
                    "id": c.id,
                    "name": c.name,
                    "type": c.connection_type,
                    "target_host": c.target_host,
                    "target_port": c.target_port,
                    "target_service": c.target_service,
                    "environment": c.environment,
                    "credential_id": c.credential_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in connections
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing infrastructure connections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@router.get("/connectors/monitoring")
async def list_monitoring_connectors():
    """List available monitoring tool connectors"""
    return {
        "available_connectors": [
            {
                "type": "datadog",
                "name": "Datadog",
                "status": "implemented",
                "description": "Cloud monitoring and alerting platform"
            },
            {
                "type": "prometheus",
                "name": "Prometheus",
                "status": "webhook_supported",
                "description": "Open-source monitoring and alerting toolkit"
            },
            {
                "type": "zabbix",
                "name": "Zabbix",
                "status": "planned",
                "description": "Enterprise monitoring solution"
            },
            {
                "type": "solarwinds",
                "name": "SolarWinds",
                "status": "planned",
                "description": "Infrastructure monitoring platform"
            },
            {
                "type": "manageengine",
                "name": "ManageEngine",
                "status": "planned",
                "description": "IT management suite"
            }
        ]
    }


@router.get("/connectors/ticketing")
async def list_ticketing_connectors():
    """List available ticketing tool connectors"""
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

