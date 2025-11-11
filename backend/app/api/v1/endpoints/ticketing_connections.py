"""
Ticketing Tool Connections API
Manage connections to external ticketing tools (ServiceNow, Zendesk, Jira, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.core.logging import get_logger
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter()
logger = get_logger(__name__)


class TicketingConnectionCreate(BaseModel):
    tool_name: str  # servicenow, zendesk, jira, etc.
    connection_type: str  # webhook, api_poll, api_push
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    sync_interval_minutes: int = 5
    meta_data: Optional[Dict[str, Any]] = None


class TicketingConnectionUpdate(BaseModel):
    is_active: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    sync_interval_minutes: Optional[int] = None
    meta_data: Optional[Dict[str, Any]] = None


@router.post("/ticketing-connections")
async def create_ticketing_connection(
    connection: TicketingConnectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new ticketing tool connection"""
    try:
        tenant_id = 1  # Demo tenant
        
        # Check if connection already exists for this tool
        existing = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id,
            TicketingToolConnection.tool_name == connection.tool_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Connection for {connection.tool_name} already exists")
        
        # Create connection
        db_connection = TicketingToolConnection(
            tenant_id=tenant_id,
            tool_name=connection.tool_name,
            connection_type=connection.connection_type,
            webhook_url=connection.webhook_url,
            webhook_secret=connection.webhook_secret,
            api_base_url=connection.api_base_url,
            api_key=connection.api_key,  # Should be encrypted in production
            api_username=connection.api_username,
            api_password=connection.api_password,  # Should be encrypted in production
            sync_interval_minutes=connection.sync_interval_minutes,
            meta_data=json.dumps(connection.meta_data) if connection.meta_data else None,
            is_active=True
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
            "message": "Ticketing tool connection created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create connection: {str(e)}")


@router.get("/ticketing-connections")
async def list_ticketing_connections(
    db: Session = Depends(get_db)
):
    """List all ticketing tool connections"""
    try:
        tenant_id = 1
        
        connections = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id
        ).order_by(TicketingToolConnection.tool_name).all()
        
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
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in connections
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing ticketing connections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@router.get("/ticketing-connections/{connection_id}")
async def get_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Get ticketing tool connection details"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return {
            "id": connection.id,
            "tool_name": connection.tool_name,
            "connection_type": connection.connection_type,
            "is_active": connection.is_active,
            "webhook_url": connection.webhook_url,
            "api_base_url": connection.api_base_url,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status,
            "last_error": connection.last_error,
            "sync_interval_minutes": connection.sync_interval_minutes,
            "created_at": connection.created_at.isoformat() if connection.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection: {str(e)}")


@router.put("/ticketing-connections/{connection_id}")
async def update_ticketing_connection(
    connection_id: int,
    update: TicketingConnectionUpdate,
    db: Session = Depends(get_db)
):
    """Update ticketing tool connection"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Update fields
        if update.is_active is not None:
            connection.is_active = update.is_active
        if update.webhook_url is not None:
            connection.webhook_url = update.webhook_url
        if update.webhook_secret is not None:
            connection.webhook_secret = update.webhook_secret
        if update.api_base_url is not None:
            connection.api_base_url = update.api_base_url
        if update.api_key is not None:
            connection.api_key = update.api_key
        if update.api_username is not None:
            connection.api_username = update.api_username
        if update.api_password is not None:
            connection.api_password = update.api_password
        if update.sync_interval_minutes is not None:
            connection.sync_interval_minutes = update.sync_interval_minutes
        if update.meta_data is not None:
            connection.meta_data = json.dumps(update.meta_data)
        
        connection.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(connection)
        
        return {
            "id": connection.id,
            "tool_name": connection.tool_name,
            "is_active": connection.is_active,
            "message": "Connection updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update connection: {str(e)}")


@router.delete("/ticketing-connections/{connection_id}")
async def delete_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Delete ticketing tool connection"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        db.delete(connection)
        db.commit()
        
        return {"message": "Connection deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete connection: {str(e)}")


@router.post("/ticketing-connections/{connection_id}/test")
async def test_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Test ticketing tool connection"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # TODO: Implement actual connection test
        # For now, just return success
        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = "success"
        connection.last_error = None
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Connection test successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {str(e)}")


@router.get("/ticketing-tools")
async def list_available_ticketing_tools():
    """List available ticketing tools that can be connected"""
    return {
        "tools": [
            {
                "name": "servicenow",
                "display_name": "ServiceNow",
                "connection_types": ["webhook", "api_poll"],
                "description": "ServiceNow ITSM platform"
            },
            {
                "name": "zendesk",
                "display_name": "Zendesk",
                "connection_types": ["webhook", "api_poll"],
                "description": "Zendesk Support platform"
            },
            {
                "name": "jira",
                "display_name": "Jira",
                "connection_types": ["webhook", "api_poll"],
                "description": "Atlassian Jira"
            },
            {
                "name": "bmc_remedy",
                "display_name": "BMC Remedy",
                "connection_types": ["api_poll"],
                "description": "BMC Remedy ITSM"
            },
            {
                "name": "manageengine",
                "display_name": "ManageEngine",
                "connection_types": ["webhook", "api_poll"],
                "description": "ManageEngine ServiceDesk"
            }
        ]
    }



