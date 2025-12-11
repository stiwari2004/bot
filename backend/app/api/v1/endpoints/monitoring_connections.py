"""
Monitoring Tool Connections API
Manage connections to external monitoring tools (Datadog, Prometheus, Azure Monitor, Splunk)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)


class MonitoringConnectionCreate(BaseModel):
    tool_name: str  # datadog, prometheus, azure_monitor, splunk
    connection_type: str  # webhook, api
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    application_key: Optional[str] = None  # For Datadog
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True


class MonitoringConnectionUpdate(BaseModel):
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    application_key: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@router.get("/monitoring-connections")
async def list_monitoring_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List monitoring tool connections for the current tenant"""
    tenant_id = current_user.tenant_id
    connections = (
        db.query(MonitoringToolConnection)
        .filter(MonitoringToolConnection.tenant_id == tenant_id)
        .all()
    )

    return {
        "connections": [
            {
                "id": c.id,
                "tool_name": c.tool_name,
                "connection_type": c.connection_type,
                "is_active": c.is_active,
                "webhook_url": c.webhook_url,
                "api_base_url": c.api_base_url,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "last_sync_status": c.last_sync_status,
                "last_error": c.last_error,
                "meta_data": c.meta_data,
            }
            for c in connections
        ]
    }


@router.post("/monitoring-connections")
async def create_monitoring_connection(
    connection: MonitoringConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new monitoring tool connection"""
    try:
        tenant_id = current_user.tenant_id

        db_connection = MonitoringToolConnection(
            tenant_id=tenant_id,
            tool_name=connection.tool_name,
            connection_type=connection.connection_type,
            is_active=connection.is_active
            if connection.is_active is not None
            else True,
            webhook_url=None,
            api_base_url=connection.api_base_url,
            api_key=connection.api_key,
            api_username=connection.api_username,
            api_password=connection.api_password,
            application_key=connection.application_key,
            meta_data=connection.meta_data,
        )

        db.add(db_connection)
        db.commit()
        db.refresh(db_connection)

        return {
            "id": db_connection.id,
            "tool_name": db_connection.tool_name,
            "connection_type": db_connection.connection_type,
            "is_active": db_connection.is_active,
            "api_base_url": db_connection.api_base_url,
            "message": "Monitoring tool connection created successfully",
        }
    except Exception as e:
        logger.error(f"Error creating monitoring connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create monitoring connection: {e}"
        )


@router.put("/monitoring-connections/{connection_id}")
async def update_monitoring_connection(
    connection_id: int,
    update: MonitoringConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing monitoring tool connection"""
    tenant_id = current_user.tenant_id

    db_connection = (
        db.query(MonitoringToolConnection)
        .filter(
            MonitoringToolConnection.id == connection_id,
            MonitoringToolConnection.tenant_id == tenant_id,
        )
        .first()
    )

    if not db_connection:
        raise HTTPException(status_code=404, detail="Monitoring connection not found")

    if update.api_base_url is not None:
        db_connection.api_base_url = update.api_base_url
    if update.api_key is not None:
        db_connection.api_key = update.api_key
    if update.api_username is not None:
        db_connection.api_username = update.api_username
    if update.api_password is not None:
        db_connection.api_password = update.api_password
    if update.application_key is not None:
        db_connection.application_key = update.application_key
    if update.meta_data is not None:
        db_connection.meta_data = update.meta_data
    if update.is_active is not None:
        db_connection.is_active = update.is_active

    db.commit()
    db.refresh(db_connection)

    return {
        "id": db_connection.id,
        "tool_name": db_connection.tool_name,
        "connection_type": db_connection.connection_type,
        "is_active": db_connection.is_active,
        "api_base_url": db_connection.api_base_url,
        "message": "Monitoring tool connection updated successfully",
    }


@router.delete("/monitoring-connections/{connection_id}")
async def delete_monitoring_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a monitoring tool connection"""
    tenant_id = current_user.tenant_id

    db_connection = (
        db.query(MonitoringToolConnection)
        .filter(
            MonitoringToolConnection.id == connection_id,
            MonitoringToolConnection.tenant_id == tenant_id,
        )
        .first()
    )

    if not db_connection:
        raise HTTPException(status_code=404, detail="Monitoring connection not found")

    db_connection.is_active = False
    db.commit()

    return {"message": "Monitoring tool connection deleted successfully"}










