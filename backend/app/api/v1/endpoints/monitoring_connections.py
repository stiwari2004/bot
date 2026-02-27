"""
Monitoring Tool Connections API
Manage connections to external monitoring tools (Datadog, Prometheus, Azure Monitor, Splunk, SolarWinds)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)


def generate_webhook_url(tool_name: str) -> str:
    """
    Generate webhook URL for a monitoring tool
    
    Args:
        tool_name: Name of the monitoring tool (e.g., 'solarwinds', 'datadog')
    
    Returns:
        Full webhook URL that the tool should POST to
    """
    base_url = settings.BACKEND_BASE_URL.rstrip('/')
    # Use /api/v1/alerts/webhook/{source} for better organization
    # Also supports /api/v1/tickets/webhook/{source} for backward compatibility
    return f"{base_url}/api/v1/alerts/webhook/{tool_name}"


class MonitoringConnectionCreate(BaseModel):
    tool_name: str  # datadog, prometheus, azure_monitor, splunk, solarwinds
    connection_type: str  # webhook, api
    webhook_url: Optional[str] = None  # Webhook URL for webhook connections
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    application_key: Optional[str] = None  # For Datadog
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True


class MonitoringConnectionUpdate(BaseModel):
    connection_type: Optional[str] = None
    api_base_url: Optional[str] = None
    webhook_url: Optional[str] = None
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
        .filter(
            MonitoringToolConnection.tenant_id == tenant_id,
            MonitoringToolConnection.is_active == True
        )
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

        # For webhook connections, automatically generate webhook URL if not provided
        webhook_url = connection.webhook_url
        if connection.connection_type == "webhook" and not webhook_url:
            webhook_url = generate_webhook_url(connection.tool_name)
            logger.info(f"Auto-generated webhook URL for {connection.tool_name}: {webhook_url}")

        db_connection = MonitoringToolConnection(
            tenant_id=tenant_id,
            tool_name=connection.tool_name,
            connection_type=connection.connection_type,
            is_active=connection.is_active
            if connection.is_active is not None
            else True,
            webhook_url=webhook_url,
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
            "webhook_url": db_connection.webhook_url,
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

    if update.connection_type is not None:
        db_connection.connection_type = update.connection_type
    if update.api_base_url is not None:
        db_connection.api_base_url = update.api_base_url
    if update.webhook_url is not None:
        db_connection.webhook_url = update.webhook_url
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
        "webhook_url": db_connection.webhook_url,
        "api_base_url": db_connection.api_base_url,
        "message": "Monitoring tool connection updated successfully",
    }


@router.delete("/monitoring-connections/{connection_id}")
async def delete_monitoring_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a monitoring tool connection"""
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

    try:
        # Hard delete the connection
        db.delete(db_connection)
        db.commit()
        logger.info(f"Deleted monitoring connection {connection_id} for tenant {tenant_id}")
        return {"message": "Monitoring tool connection deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting monitoring connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete monitoring connection: {str(e)}")


@router.post("/monitoring-connections/{connection_id}/test")
async def test_monitoring_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test a monitoring tool connection"""
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

    # For webhook connections, skip authentication test
    if db_connection.connection_type == "webhook":
        webhook_url = db_connection.webhook_url or generate_webhook_url(db_connection.tool_name)
        # Update webhook_url if it wasn't set
        if not db_connection.webhook_url:
            db_connection.webhook_url = webhook_url
            db.commit()
        return {
            "success": True,
            "message": f"Webhook connection configured. Use this URL in {db_connection.tool_name}: {webhook_url}",
            "webhook_url": webhook_url
        }

    try:
        if db_connection.tool_name == "solarwinds":
            from app.services.monitoring_connectors.solarwinds import SolarWindsConnector
            from app.services.monitoring_connectors.solarwinds_types import SolarWindsConnectionConfig
            import json
            
            meta_data = json.loads(db_connection.meta_data) if isinstance(db_connection.meta_data, str) else (db_connection.meta_data or {})
            config = SolarWindsConnectionConfig(
                api_base_url=db_connection.api_base_url or meta_data.get("api_base_url", ""),
                username=meta_data.get("username") or db_connection.api_username,
                password=meta_data.get("password") or db_connection.api_password,
                api_key=meta_data.get("api_key") or db_connection.api_key,
                oauth_client_id=meta_data.get("client_id"),
                oauth_client_secret=meta_data.get("client_secret"),
            )
            
            # Validate that we have at least one authentication method
            if not config.api_base_url:
                return {"success": False, "message": "API Base URL is required for API connections"}
            
            if not (config.api_key or (config.username and config.password) or (config.oauth_client_id and config.oauth_client_secret)):
                return {"success": False, "message": "No valid authentication method found. Please provide API Key, Username/Password, or OAuth credentials."}
            
            connector = SolarWindsConnector()
            result = await connector.test_connection(config)
            await connector.close()
            
            return result
        elif db_connection.tool_name == "opmanager":
            from app.services.monitoring_connectors.opmanager import OpManagerConnector

            base_url = db_connection.api_base_url
            api_key = db_connection.api_key

            if not base_url:
                return {"success": False, "message": "API Base URL is required for OpManager connections"}
            if not api_key:
                return {"success": False, "message": "API key is required for OpManager connections"}

            connector = OpManagerConnector()
            result = await connector.test_connection(base_url=base_url, api_key=api_key)
            await connector.close()
            return result
        elif db_connection.tool_name == "datadog":
            if not db_connection.api_key or not db_connection.application_key:
                return {"success": False, "message": "API Key and Application Key are required for Datadog connections"}
            # TODO: Implement Datadog connection test
            return {"success": True, "message": "Datadog connection test not yet implemented"}
        else:
            return {"success": False, "message": f"Test connection not implemented for {db_connection.tool_name}"}
    except Exception as e:
        logger.error(f"Error testing monitoring connection: {e}", exc_info=True)
        return {"success": False, "message": f"Connection test failed: {str(e)}"}






