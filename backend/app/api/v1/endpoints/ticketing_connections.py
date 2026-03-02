"""
Ticketing Tool Connections API
Manage connections to external ticketing tools (ServiceNow, Zendesk, Jira, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.core.config import settings
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.models.user import User
from app.services.auth import get_current_user
from app.core.logging import get_logger
from app.services.ticketing_connectors.zoho_oauth import ZohoOAuthService
from app.services.ticketing_poller import TicketingPoller
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import secrets

router = APIRouter()
logger = get_logger(__name__)
oauth_service = ZohoOAuthService()

# Global poller instance for manual sync
_poller_instance: Optional[TicketingPoller] = None


def _parse_meta_data_safe(raw: Any) -> Dict[str, Any]:
    """Parse connection meta_data to a dict; never raise. Handles None, empty string, 'null', invalid JSON."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid ticketing connection meta_data JSON, using empty dict")
        return {}


def _sync_servicenow_credentials(connection: TicketingToolConnection, meta_data: Dict[str, Any], db: Session) -> bool:
    """Sync ServiceNow credentials from api_username/api_password to meta_data if missing. Returns True if synced."""
    if connection.tool_name != "servicenow":
        return False
    
    synced = False
    if not meta_data.get("username") and connection.api_username:
        meta_data["username"] = connection.api_username
        synced = True
    if not meta_data.get("password") and connection.api_password:
        meta_data["password"] = connection.api_password
        synced = True
    
    if synced:
        connection.meta_data = json.dumps(meta_data)
        db.commit()
        logger.info(f"Synced ServiceNow credentials from connection fields to meta_data for connection {connection.id}")
    
    return synced


@router.get("/ticketing-tools")
async def list_ticketing_tools():
    """List available ticketing tools that can be connected"""
    return {
        "tools": [
            {
                "name": "servicenow",
                "display_name": "ServiceNow",
                "description": "ServiceNow ITSM platform",
                "connection_types": ["api_poll", "webhook"],
                "auth_methods": ["basic_auth", "oauth2"],
                "icon": "servicenow"
            },
            {
                "name": "zoho",
                "display_name": "Zoho Desk",
                "description": "Zoho Desk ticketing system",
                "connection_types": ["api_poll"],
                "auth_methods": ["oauth2"],
                "icon": "zoho"
            },
            {
                "name": "manageengine",
                "display_name": "ManageEngine ServiceDesk Plus",
                "description": "ManageEngine ServiceDesk Plus",
                "connection_types": ["api_poll"],
                "auth_methods": ["oauth2"],
                "icon": "manageengine"
            },
            {
                "name": "jira",
                "display_name": "Jira",
                "description": "Atlassian Jira issue tracker",
                "connection_types": ["api_poll", "webhook"],
                "auth_methods": ["api_token", "oauth2"],
                "icon": "jira"
            },
            {
                "name": "zendesk",
                "display_name": "Zendesk",
                "description": "Zendesk customer support platform",
                "connection_types": ["api_poll", "webhook"],
                "auth_methods": ["api_token", "oauth2"],
                "icon": "zendesk"
            }
        ]
    }

def get_poller_instance() -> TicketingPoller:
    """Get or create poller instance for manual sync"""
    global _poller_instance
    if _poller_instance is None:
        _poller_instance = TicketingPoller()
    return _poller_instance


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
    # OAuth fields (for Zoho)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    # Meta data (for tool-specific fields like api_secret for ManageEngine)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ticketing tool connection"""
    try:
        tenant_id = current_user.tenant_id
        
        # Check if connection already exists for this tool
        existing = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id,
            TicketingToolConnection.tool_name == connection.tool_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Connection for {connection.tool_name} already exists")
        
        # Build meta_data with OAuth fields if provided
        meta_data = connection.meta_data or {}
        
        # Zoho and ManageEngine v2 both use OAuth 2.0 (same flow)
        if connection.tool_name == "zoho" and connection.client_id:
            meta_data.update({
                "client_id": connection.client_id,
                "client_secret": connection.client_secret,
                "redirect_uri": connection.redirect_uri or settings.OAUTH_CALLBACK_URL
            })
        elif connection.tool_name == "manageengine":
            # For ManageEngine we support two modes:
            # - v2 (OAuth 2.0 via Zoho accounts)  [legacy / current behaviour]
            # - v3 (API key / authtoken)
            version = (connection.meta_data or {}).get("version") if isinstance(connection.meta_data, dict) else None
            if not version and isinstance(connection.meta_data, str):
                try:
                    parsed_meta = json.loads(connection.meta_data)
                    version = parsed_meta.get("version")
                except Exception:
                    version = None
            # Default to v2 (OAuth) for backward compatibility if version not set
            version = version or "v2"
            if version == "v2" and connection.client_id:
                meta_data.update({
                    "client_id": connection.client_id,
                    "client_secret": connection.client_secret,
                    "redirect_uri": connection.redirect_uri or settings.OAUTH_CALLBACK_URL,
                    "version": "v2",
                })
            else:
                # v3 / API key mode: ensure version is recorded; API key itself is stored in
                # api_key/api_username fields and used by the fetcher.
                meta_data.setdefault("version", "v3")
        
        # For ServiceNow, sync api_username/api_password to meta_data (ServiceNow fetcher expects credentials in meta_data)
        if connection.tool_name == "servicenow":
            if connection.api_username and connection.api_password:
                meta_data["username"] = connection.api_username
                meta_data["password"] = connection.api_password
                logger.info(f"Synced ServiceNow credentials to meta_data for new connection. Username length: {len(connection.api_username)}")
        
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
            meta_data=json.dumps(meta_data) if meta_data else None,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all ticketing tool connections for the current tenant"""
    try:
        tenant_id = current_user.tenant_id
        
        connections = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id
        ).order_by(TicketingToolConnection.tool_name).all()
        
        result = []
        for c in connections:
            meta_data = _parse_meta_data_safe(c.meta_data)
            oauth_authorized = False
            oauth_supported = False
            if c.tool_name == "zoho":
                # Zoho is always OAuth 2.0
                oauth_supported = True
                # Zoho is authorized if access_token exists (stored after OAuth callback)
                oauth_authorized = bool(meta_data.get("access_token"))
            elif c.tool_name == "manageengine":
                # ManageEngine supports:
                # - v2: OAuth 2.0 (authorization code flow)
                # - v3: API key/authtoken (no OAuth)
                version = str(meta_data.get("version", "v2")).lower()
                if version == "v2":
                    oauth_supported = True
                    oauth_authorized = bool(meta_data.get("access_token"))
            elif c.tool_name == "servicenow":
                # ServiceNow is authorized if credentials exist (username/password or OAuth client_id/secret)
                # Check both meta_data and connection fields
                has_username = bool(meta_data.get("username") or c.api_username)
                has_password = bool(meta_data.get("password") or c.api_password)
                has_oauth = bool(meta_data.get("client_id") and meta_data.get("client_secret"))
                # Authorized if we have either Basic Auth credentials OR OAuth credentials
                oauth_authorized = (has_username and has_password) or has_oauth
            
            result.append({
                "id": c.id,
                "tool_name": c.tool_name,
                "connection_type": c.connection_type,
                "is_active": c.is_active,
                "webhook_url": c.webhook_url,
                "api_base_url": c.api_base_url,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "last_sync_status": c.last_sync_status,
                "last_error": c.last_error,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "oauth_authorized": oauth_authorized,
                "oauth_supported": oauth_supported,
            })
        
        return {
            "connections": result
        }
        
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
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        meta_data = _parse_meta_data_safe(connection.meta_data)
        oauth_authorized = False
        oauth_supported = False
        if connection.tool_name == "zoho":
            oauth_supported = True
            oauth_authorized = bool(meta_data.get("access_token"))
        elif connection.tool_name == "manageengine":
            version = str(meta_data.get("version", "v2")).lower()
            if version == "v2":
                oauth_supported = True
                oauth_authorized = bool(meta_data.get("access_token"))
        elif connection.tool_name == "servicenow":
            # ServiceNow is authorized if credentials exist (username/password or OAuth client_id/secret)
            has_username = bool(meta_data.get("username") or connection.api_username)
            has_password = bool(meta_data.get("password") or connection.api_password)
            has_oauth = bool(meta_data.get("client_id") and meta_data.get("client_secret"))
            oauth_authorized = (has_username and has_password) or has_oauth
        
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
            "created_at": connection.created_at.isoformat() if connection.created_at else None,
            "oauth_authorized": oauth_authorized,
            "oauth_supported": oauth_supported,
        }
        
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
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Update fields
        if connection_update.is_active is not None:
            connection.is_active = connection_update.is_active
        if connection_update.webhook_url is not None:
            connection.webhook_url = connection_update.webhook_url
        if connection_update.webhook_secret is not None:
            connection.webhook_secret = connection_update.webhook_secret
        if connection_update.api_base_url is not None:
            connection.api_base_url = connection_update.api_base_url
        if connection_update.api_key is not None:
            connection.api_key = connection_update.api_key
        if connection_update.api_username is not None:
            connection.api_username = connection_update.api_username
        if connection_update.api_password is not None:
            connection.api_password = connection_update.api_password
        if connection_update.sync_interval_minutes is not None:
            connection.sync_interval_minutes = connection_update.sync_interval_minutes
        
        # Get or create existing_meta for ServiceNow sync
        existing_meta = None
        if connection.tool_name == "servicenow" and (connection_update.api_username is not None or connection_update.api_password is not None):
            existing_meta = _parse_meta_data_safe(connection.meta_data)
        
        # Update meta_data if provided
        if connection_update.meta_data is not None:
            # Merge with existing meta_data
            if existing_meta is None:
                existing_meta = _parse_meta_data_safe(connection.meta_data)
            existing_meta.update(connection_update.meta_data)
            connection.meta_data = json.dumps(existing_meta)
            logger.info(f"Updated meta_data for {connection.tool_name} connection {connection.id}. Keys: {list(existing_meta.keys())}")
        
        # For ServiceNow, also sync api_username/api_password to meta_data (if not already in meta_data from above)
        if connection.tool_name == "servicenow":
            if existing_meta is None:
                existing_meta = _parse_meta_data_safe(connection.meta_data)
            updated = False
            if connection_update.api_username is not None:
                existing_meta["username"] = connection_update.api_username
                updated = True
            if connection_update.api_password is not None:
                existing_meta["password"] = connection_update.api_password
                updated = True
            if updated:
                connection.meta_data = json.dumps(existing_meta)
                logger.info(f"Synced ServiceNow credentials to meta_data for connection {connection.id}. Keys: {list(existing_meta.keys())}")
        
        db.commit()
        db.refresh(connection)
        
        return {
            "id": connection.id,
            "tool_name": connection.tool_name,
            "connection_type": connection.connection_type,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a ticketing tool connection"""
    try:
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        db.delete(connection)
        db.commit()
        
        return {
            "message": "Connection deleted successfully"
        }
        
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
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        meta_data = _parse_meta_data_safe(connection.meta_data)
        
        # For Zoho and ManageEngine, check if OAuth is needed
        if connection.tool_name in ("zoho", "manageengine"):
            # For Zoho and ManageEngine v2 (OAuth mode), require OAuth before testing.
            if connection.tool_name == "zoho":
                requires_oauth = True
            else:
                version = str(meta_data.get("version", "v2")).lower()
                requires_oauth = version == "v2"

            if requires_oauth and not meta_data.get("access_token"):
                return {
                    "status": "oauth_required",
                    "message": "OAuth authorization required. Please use the authorize endpoint first."
                }
        
        # Actually fetch tickets to test the connection
        tickets_fetched = 0
        error_message = None
        
        try:
            if connection.tool_name == "zoho":
                from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
                fetcher = ZohoTicketFetcher()
                try:
                    tickets = await fetcher.fetch_tickets(
                        connection_meta=meta_data,
                        api_base_url=connection.api_base_url,
                        since=None,  # Fetch recent tickets
                        limit=10  # Just test with a few tickets
                    )
                    tickets_fetched = len(tickets)
                    await fetcher.close()
                except Exception as e:
                    await fetcher.close()
                    raise
            
            elif connection.tool_name == "manageengine":
                from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
                fetcher = ManageEngineTicketFetcher()
                try:
                    # ManageEngine supports both OAuth (v2) and API key/authtoken (v3).
                    # For testing, include a small time window so we always send a valid
                    # search_criteria block that ManageEngine accepts (modified_time.value > since_ms).
                    test_since = datetime.utcnow() - timedelta(days=7)
                    tickets = await fetcher.fetch_tickets(
                        api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                        connection_meta=meta_data,
                        api_key=connection.api_key,
                        api_username=connection.api_username,
                        api_password=connection.api_password,
                        since=test_since,
                        limit=10  # Just test with a few tickets
                    )
                    tickets_fetched = len(tickets)
                    await fetcher.close()
                except Exception as e:
                    await fetcher.close()
                    raise
            
            elif connection.tool_name == "servicenow":
                from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
                fetcher = ServiceNowTicketFetcher()
                try:
                    # ServiceNow supports OAuth 2.0 or Basic Auth
                    # Sync credentials from connection fields to meta_data if missing (for backward compatibility)
                    _sync_servicenow_credentials(connection, meta_data, db)
                    username = meta_data.get("username") or connection.api_username
                    password = meta_data.get("password") or connection.api_password
                    
                    logger.info(f"ServiceNow test - username: {'present' if username else 'missing'}, password: {'present' if password else 'missing'}")
                    logger.info(f"ServiceNow test - api_username: {'present' if connection.api_username else 'missing'}, api_password: {'present' if connection.api_password else 'missing'}")
                    logger.info(f"ServiceNow test - meta_data keys: {list(meta_data.keys())}")
                    if not username or not password:
                        error_detail = (
                            f"ServiceNow connection {connection.id} missing credentials. "
                            f"api_username: {'set' if connection.api_username else 'missing'}, "
                            f"api_password: {'set' if connection.api_password else 'missing'}, "
                            f"meta_data.username: {'set' if meta_data.get('username') else 'missing'}, "
                            f"meta_data.password: {'set' if meta_data.get('password') else 'missing'}"
                        )
                        logger.error(error_detail)
                        raise ValueError("ServiceNow credentials (username/password) are required for Basic Auth. Please update the connection with valid credentials.")
                    
                    tickets = await fetcher.fetch_tickets(
                        api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                        connection_meta=meta_data,
                        username=username,
                        password=password,
                        client_id=meta_data.get("client_id"),
                        client_secret=meta_data.get("client_secret"),
                        since=None,  # Fetch recent tickets
                        limit=10  # Just test with a few tickets
                    )
                    tickets_fetched = len(tickets)
                    await fetcher.close()
                except Exception as e:
                    await fetcher.close()
                    raise
            
            else:
                # For other tools, just mark success without fetching
                tickets_fetched = 0
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error fetching tickets during test: {e}")
            connection.last_sync_at = datetime.utcnow()
            connection.last_sync_status = "error"
            connection.last_error = error_message
            db.commit()
            
            return {
                "status": "error",
                "message": f"Connection test failed: {error_message}",
                "tickets_fetched": 0
            }
        
        # Update connection status
        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = "success"
        connection.last_error = None
        db.commit()
        
        return {
            "status": "success",
            "message": f"Connection test successful. Fetched {tickets_fetched} tickets.",
            "tickets_fetched": tickets_fetched
        }
        
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
    """Manually trigger sync for a ticketing tool connection (actually creates tickets)"""
    try:
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        if not connection.is_active:
            raise HTTPException(status_code=400, detail="Connection is not active")
        
        if connection.connection_type != "api_poll":
            raise HTTPException(status_code=400, detail="Manual sync only available for api_poll connections")
        
        logger.info(f"Manual sync triggered for {connection.tool_name} connection {connection_id}")
        
        # Use the poller service to actually sync (this creates tickets in database)
        poller = get_poller_instance()
        await poller._poll_connection(connection, db)
        
        # Refresh connection to get updated stats
        db.refresh(connection)
        
        return {
            "status": "success",
            "message": f"Sync completed for {connection.tool_name} connection",
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status
        }
        
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
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")
        
        meta_data = _parse_meta_data_safe(connection.meta_data)

        # For ManageEngine, only v3 connections use OAuth; v2 uses API key/authtoken.
        if connection.tool_name == "manageengine":
            version = str(meta_data.get("version", "v2")).lower()
            if version == "v3":
                raise HTTPException(
                    status_code=400,
                    detail="OAuth is not supported for ManageEngine v3 (API key) connections. "
                           "Switch this connection to v2 in the settings to use OAuth."
                )
        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials (client_id, client_secret) not configured")
        
        # Generate state token for CSRF protection and encode connection_id so global callback can resolve it.
        # Format: "<connection_id>:<random>"
        raw_state = secrets.token_urlsafe(32)
        state_token = f"{connection_id}:{raw_state}"
        
        # Determine Zoho domain based on tool
        zoho_domain = "com"  # Default
        if connection.tool_name == "manageengine":
            zoho_domain = meta_data.get("zoho_domain", "in")  # ManageEngine typically uses .in
        
        # Build OAuth authorization URL
        # ManageEngine ServiceDesk Plus OnDemand uses SDPOnDemand.* scopes per docs:
        # https://www.manageengine.com/products/service-desk/sdpod-v3-api/getting-started/oauth-2.0.html
        if connection.tool_name == "manageengine":
            scope = "SDPOnDemand.requests.ALL,SDPOnDemand.general.READ"
        else:
            scope = "Desk.tickets.READ,Desk.tickets.WRITE,Desk.tickets.UPDATE"
        auth_url = f"https://accounts.zoho.{zoho_domain}/oauth/v2/auth"
        params = {
            "scope": scope,
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "access_type": "offline",
            "state": state_token
        }
        
        # For GET request, redirect to OAuth
        if request.method == "GET":
            from urllib.parse import urlencode
            full_url = f"{auth_url}?{urlencode(params)}"
            return RedirectResponse(url=full_url)
        
        # For POST request, return the URL
        from urllib.parse import urlencode
        full_url = f"{auth_url}?{urlencode(params)}"
        return {
            "authorization_url": full_url,
            "state": state_token,
            "message": "Visit the authorization_url to authorize the connection"
        }
        
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
        tenant_id = current_user.tenant_id
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")
        
        meta_data = _parse_meta_data_safe(connection.meta_data)
        if connection.tool_name == "manageengine":
            version = str(meta_data.get("version", "v2")).lower()
            if version == "v3":
                raise HTTPException(
                    status_code=400,
                    detail="OAuth is not supported for ManageEngine v3 (API key) connections. "
                           "Switch this connection to v2 in the settings to use OAuth."
                )
        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials not configured")
        
        # Determine Zoho domain
        zoho_domain = "com"
        if connection.tool_name == "manageengine":
            zoho_domain = meta_data.get("zoho_domain", "in")
        
        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            domain=zoho_domain
        )
        
        # Update connection with tokens
        meta_data.update(tokens)
        connection.meta_data = json.dumps(meta_data)
        db.commit()
        
        return {
            "status": "success",
            "message": "OAuth authorization successful",
            "connection_id": connection_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process OAuth callback: {str(e)}")


async def oauth_callback_public(
    code: str,
    state: Optional[str],
    db: Session,
):
    """
    Public OAuth callback used by /oauth/callback (no auth, connection_id encoded in state).
    State format (set in authorize_ticketing_connection): "<connection_id>:<random>"
    """
    try:
        if not state or ":" not in state:
            logger.warning(f"OAuth callback received state without connection_id (legacy or expired). state={state[:50] if state else ''!r}")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state. Please open the connection in Resolvify and click Authorize again."
            )
        parts = state.split(":", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid OAuth state; connection_id missing")
        connection_id_str, _ = parts[0], parts[1]
        try:
            connection_id = int(connection_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid connection_id in OAuth state")

        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id
        ).first()

        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")

        meta_data = _parse_meta_data_safe(connection.meta_data)
        if connection.tool_name == "manageengine":
            version = str(meta_data.get("version", "v2")).lower()
            if version == "v3":
                raise HTTPException(
                    status_code=400,
                    detail="OAuth is not supported for ManageEngine v3 (API key) connections. "
                           "Switch this connection to v2 in the settings to use OAuth."
                )
        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL

        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials not configured")

        # Determine Zoho domain
        zoho_domain = "com"
        if connection.tool_name == "manageengine":
            zoho_domain = meta_data.get("zoho_domain", "in")

        # Exchange code for tokens (use domain-specific Zoho URL per ManageEngine docs)
        try:
            tokens = await oauth_service.exchange_code_for_tokens(
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                domain=zoho_domain
            )
        except Exception as token_err:
            logger.warning(f"OAuth token exchange failed: {token_err}")
            raise HTTPException(
                status_code=400,
                detail=f"Authorization failed: {str(token_err)}. Check redirect URI and client credentials."
            )

        # Update connection with tokens
        meta_data.update(tokens)
        connection.meta_data = json.dumps(meta_data)
        db.commit()

        # Front-channel OAuth flow: send user back to frontend app on success.
        # Use tab=settings so Settings & Connections view is opened automatically.
        redirect_url = f"{settings.FRONTEND_BASE_URL}/?tab=settings&oauth_success=1&connection_id={connection_id}"
        return RedirectResponse(url=redirect_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing public OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process OAuth callback: {str(e)}")
