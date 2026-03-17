"""
Ticketing Tool Connections API
Manage connections to external ticketing tools (ServiceNow, Zendesk, Jira, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger
from app.controllers.ticketing_connection_controller import get_ticketing_connection_controller
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)


class TicketingConnectionCreate(BaseModel):
    tool_name: str
    connection_type: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    sync_interval_minutes: int = 5
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
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


@router.get("/ticketing-tools")
async def list_ticketing_tools():
    """List available ticketing tools that can be connected"""
    return {
        "tools": [
            {"name": "servicenow", "display_name": "ServiceNow", "description": "ServiceNow ITSM platform", "connection_types": ["api_poll", "webhook"], "auth_methods": ["basic_auth", "oauth2"], "icon": "servicenow"},
            {"name": "zoho", "display_name": "Zoho Desk", "description": "Zoho Desk ticketing system", "connection_types": ["api_poll"], "auth_methods": ["oauth2"], "icon": "zoho"},
            {"name": "manageengine", "display_name": "ManageEngine ServiceDesk Plus", "description": "ManageEngine ServiceDesk Plus", "connection_types": ["api_poll"], "auth_methods": ["oauth2"], "icon": "manageengine"},
            {"name": "jira", "display_name": "Jira", "description": "Atlassian Jira issue tracker", "connection_types": ["api_poll", "webhook"], "auth_methods": ["api_token", "oauth2"], "icon": "jira"},
            {"name": "zendesk", "display_name": "Zendesk", "description": "Zendesk customer support platform", "connection_types": ["api_poll", "webhook"], "auth_methods": ["api_token", "oauth2"], "icon": "zendesk"},
        ]
    }


@router.post("/ticketing-connections")
async def create_ticketing_connection(
    connection: TicketingConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ticketing tool connection"""
    try:
        return get_ticketing_connection_controller(db, current_user.tenant_id).create_connection(connection)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create connection: {str(e)}")


@router.get("/ticketing-connections")
async def list_ticketing_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all ticketing tool connections for the current tenant"""
    try:
        return get_ticketing_connection_controller(db, current_user.tenant_id).list_connections()
    except Exception as e:
        logger.error(f"Error listing ticketing connections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@router.get("/ticketing-connections/{connection_id}")
async def get_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ticketing tool connection"""
    try:
        return get_ticketing_connection_controller(db, current_user.tenant_id).get_connection(connection_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get connection: {str(e)}")


@router.put("/ticketing-connections/{connection_id}")
@router.patch("/ticketing-connections/{connection_id}")
async def update_ticketing_connection(
    connection_id: int,
    connection_update: TicketingConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a ticketing tool connection"""
    try:
        return get_ticketing_connection_controller(db, current_user.tenant_id).update_connection(connection_id, connection_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update connection: {str(e)}")


@router.delete("/ticketing-connections/{connection_id}")
async def delete_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a ticketing tool connection"""
    try:
        return get_ticketing_connection_controller(db, current_user.tenant_id).delete_connection(connection_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete connection: {str(e)}")


@router.post("/ticketing-connections/{connection_id}/test")
async def test_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test ticketing tool connection by actually fetching tickets"""
    try:
        return await get_ticketing_connection_controller(db, current_user.tenant_id).test_connection(connection_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing ticketing connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {str(e)}")


@router.post("/ticketing-connections/{connection_id}/sync")
async def sync_ticketing_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger sync for a ticketing tool connection"""
    try:
        return await get_ticketing_connection_controller(db, current_user.tenant_id).sync_connection(connection_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing ticketing connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync connection: {str(e)}")


@router.get("/ticketing-connections/{connection_id}/oauth/authorize")
@router.post("/ticketing-connections/{connection_id}/oauth/authorize")
async def authorize_ticketing_connection(
    connection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """OAuth authorization endpoint for ticketing tools (Zoho, ManageEngine)"""
    try:
        controller = get_ticketing_connection_controller(db, current_user.tenant_id)
        result = controller.build_oauth_authorize_url(connection_id, method=request.method)
        if request.method == "GET":
            return RedirectResponse(url=result["redirect_url"])
        return {"authorization_url": result["authorization_url"], "state": result["state"], "message": "Visit the authorization_url to authorize the connection"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating OAuth authorization URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")


@router.get("/ticketing-connections/{connection_id}/oauth/callback")
async def oauth_callback(
    connection_id: int,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """OAuth callback endpoint for ticketing tools"""
    try:
        return await get_ticketing_connection_controller(db, current_user.tenant_id).exchange_oauth_callback(
            connection_id=connection_id, code=code, state=state
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process OAuth callback: {str(e)}")


async def oauth_callback_public(code: str, state: Optional[str], db: Session):
    """
    Public OAuth callback used by /oauth/callback (no auth, connection_id encoded in state).
    Delegates to controller.handle_public_oauth_callback().
    """
    from app.controllers.ticketing_connection_controller import TicketingConnectionController
    controller = TicketingConnectionController(db, tenant_id=0)
    return await controller.handle_public_oauth_callback(code=code, state=state)
