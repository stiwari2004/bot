"""
Ticketing Tool Connections API
Manage connections to external ticketing tools (ServiceNow, Zendesk, Jira, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.core.database import get_db
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.core.logging import get_logger
from app.services.ticketing_connectors.zoho_oauth import ZohoOAuthService
from pydantic import BaseModel
from datetime import datetime
import json
import secrets

router = APIRouter()
logger = get_logger(__name__)
oauth_service = ZohoOAuthService()


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
        
        # Build meta_data with OAuth fields if provided
        meta_data = connection.meta_data or {}
        
        # Zoho and ManageEngine both use OAuth 2.0 (same flow)
        if (connection.tool_name == "zoho" or connection.tool_name == "manageengine") and connection.client_id:
            meta_data.update({
                "client_id": connection.client_id,
                "client_secret": connection.client_secret,
                "redirect_uri": connection.redirect_uri or "http://localhost:8000/oauth/callback"
            })
        elif connection.tool_name == "manageengine":
            # Legacy: Store API credentials in meta_data for ManageEngine (if not using OAuth)
            # Frontend sends api_secret in meta_data, preserve it
            if connection.api_key:
                meta_data["api_key"] = connection.api_key
            if connection.api_username:
                meta_data["api_username"] = connection.api_username
            # api_secret should already be in meta_data from frontend
        
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
    db: Session = Depends(get_db)
):
    """List all ticketing tool connections"""
    try:
        tenant_id = 1
        
        connections = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id
        ).order_by(TicketingToolConnection.tool_name).all()
        
        result = []
        for c in connections:
            meta_data = json.loads(c.meta_data) if c.meta_data else {}
            oauth_authorized = False
            if c.tool_name == "zoho":
                # Zoho is authorized if access_token exists (stored after OAuth callback)
                oauth_authorized = bool(meta_data.get("access_token"))
            elif c.tool_name == "manageengine":
                # ManageEngine is authorized if access_token exists (stored after OAuth callback, same as Zoho)
                oauth_authorized = bool(meta_data.get("access_token"))
            
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
                "oauth_authorized": oauth_authorized
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
        
        meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
        oauth_authorized = False
        if connection.tool_name == "zoho":
            # Zoho is authorized if access_token exists (stored after OAuth callback)
            oauth_authorized = bool(meta_data.get("access_token"))
        elif connection.tool_name == "manageengine":
            # ManageEngine is authorized if access_token exists (stored after OAuth callback, same as Zoho)
            oauth_authorized = bool(meta_data.get("access_token"))
        
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
            "created_at": connection.created_at.isoformat() if connection.created_at else None,
            "oauth_authorized": oauth_authorized
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
    """Test ticketing tool connection by actually fetching tickets"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
        
        # For Zoho and ManageEngine, check if OAuth is needed
        if connection.tool_name in ("zoho", "manageengine"):
            if not meta_data.get("access_token"):
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
                    # ManageEngine now uses OAuth 2.0 (same as Zoho)
                    tickets = await fetcher.fetch_tickets(
                        api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                        connection_meta=meta_data,
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


@router.get("/ticketing-connections/{connection_id}/oauth/authorize")
async def authorize_oauth_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Generate OAuth authorization URL for Zoho connection or login URL for ManageEngine"""
    try:
        tenant_id = 1
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Zoho OAuth flow
        if connection.tool_name == "zoho":
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
            client_id = meta_data.get("client_id")
            redirect_uri = meta_data.get("redirect_uri", "http://localhost:8000/oauth/callback")
            zoho_domain = meta_data.get("zoho_domain", "com")  # Default to .com, but support .in for Indian accounts
            
            if not client_id:
                raise HTTPException(status_code=400, detail="Client ID not configured. Please update connection with OAuth credentials.")
            
            # Generate state for CSRF protection
            state = f"{connection_id}:{secrets.token_urlsafe(32)}"
            
            # Generate authorization URL with domain
            auth_url = oauth_service.generate_authorization_url(
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                domain=zoho_domain
            )
            
            # Store state in meta_data temporarily
            meta_data["oauth_state"] = state
            connection.meta_data = json.dumps(meta_data)
            db.commit()
            
            return {
                "authorization_url": auth_url,
                "state": state
            }
        
        # ManageEngine OAuth flow (uses same OAuth as Zoho)
        elif connection.tool_name == "manageengine":
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
            client_id = meta_data.get("client_id")
            redirect_uri = meta_data.get("redirect_uri", "http://localhost:8000/oauth/callback")
            # ManageEngine often uses .in domain (India), default to .in for ManageEngine
            zoho_domain = meta_data.get("zoho_domain", "in")  # Default to .in for ManageEngine (Indian accounts)
            
            if not client_id:
                raise HTTPException(
                    status_code=400,
                    detail="Client ID not configured. Please update connection with OAuth credentials (Client ID and Client Secret)."
                )
            
            # Generate state for CSRF protection
            state = f"{connection_id}:{secrets.token_urlsafe(32)}"
            
            # ManageEngine ServiceDesk Plus Cloud uses OAuth 2.0 with Zoho accounts
            # Use the same OAuth service as Zoho, but with ManageEngine-specific scopes
            scopes = ["SDPOnDemand.requests.ALL"]  # ManageEngine scope format
            
            auth_url = oauth_service.generate_authorization_url(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scopes=scopes,
                state=state,
                domain=zoho_domain
            )
            
            # Store state in meta_data temporarily
            meta_data["oauth_state"] = state
            connection.meta_data = json.dumps(meta_data)
            db.commit()
            
            logger.info(f"Generated ManageEngine OAuth authorization URL for connection {connection_id}")
            
            return {
                "authorization_url": auth_url,
                "state": state
            }
        
        else:
            raise HTTPException(status_code=400, detail="Authorization is only supported for Zoho and ManageEngine")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating authorization URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback from Zoho or ManageEngine"""
    logger.info(f"OAuth callback received - code: {code[:20]}..., state: {state[:50]}..., error: {error}")
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(url=f"http://localhost:3000/?tab=settings&oauth_error={error}")
        
        # Extract connection_id from state
        if ":" not in state:
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=invalid_state")
        
        connection_id_str, _ = state.split(":", 1)
        try:
            connection_id = int(connection_id_str)
        except ValueError:
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=invalid_state")
        
        tenant_id = 1
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.id == connection_id,
            TicketingToolConnection.tenant_id == tenant_id
        ).first()
        
        if not connection:
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=connection_not_found")
        
        # Support both Zoho and ManageEngine (both use same OAuth flow)
        if connection.tool_name not in ("zoho", "manageengine"):
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=invalid_tool")
        
        meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
        stored_state = meta_data.get("oauth_state")
        
        # Verify state
        if stored_state != state:
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=state_mismatch")
        
        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri", "http://localhost:8000/oauth/callback")
        # Get domain (default to .in for ManageEngine, .com for Zoho)
        zoho_domain = meta_data.get("zoho_domain")
        if not zoho_domain:
            # Default based on tool: .in for ManageEngine (often Indian accounts), .com for Zoho
            zoho_domain = "in" if connection.tool_name == "manageengine" else "com"
        
        if not client_id or not client_secret:
            logger.error(f"OAuth callback: Missing credentials for connection {connection_id}. client_id={bool(client_id)}, client_secret={bool(client_secret)}")
            logger.error(f"OAuth callback: meta_data keys: {list(meta_data.keys())}")
            return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=missing_credentials")
        
        # Log client ID (first 10 chars only for security) and redirect URI for debugging
        logger.info(f"OAuth callback: Exchange token for connection {connection_id}, tool={connection.tool_name}, domain={zoho_domain}, client_id={client_id[:10]}..., redirect_uri={redirect_uri}")
        
        # Exchange code for tokens
        try:
            logger.info(f"Attempting to exchange OAuth code for connection {connection_id} using domain: {zoho_domain}")
            token_data = await oauth_service.exchange_code_for_tokens(
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                domain=zoho_domain
            )
            
            logger.info(f"Token exchange successful for connection {connection_id}")
            
            # Update meta_data with tokens
            meta_data.update(token_data)
            meta_data.pop("oauth_state", None)  # Remove temporary state
            connection.meta_data = json.dumps(meta_data)
            connection.last_sync_at = datetime.utcnow()
            connection.last_sync_status = "success"
            connection.last_error = None
            
            try:
                db.commit()
                logger.info(f"Database updated for connection {connection_id}")
            except Exception as commit_error:
                logger.error(f"Failed to commit OAuth tokens to database: {commit_error}", exc_info=True)
                db.rollback()
                return RedirectResponse(url=f"http://localhost:3000/?tab=settings&oauth_error=database_error")
            
            logger.info(f"OAuth authorization successful for connection {connection_id}")
            return RedirectResponse(url=f"http://localhost:3000/?tab=settings&oauth_success=true&connection_id={connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to exchange OAuth code: {e}", exc_info=True)
            try:
                connection.last_error = str(e)[:500]  # Limit error length
                connection.last_sync_status = "failed"
                db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to save error to database: {commit_error}")
                db.rollback()
            return RedirectResponse(url=f"http://localhost:3000/?tab=settings&oauth_error=token_exchange_failed")
        
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {e}")
        return RedirectResponse(url="http://localhost:3000/?tab=settings&oauth_error=internal_error")


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
            },
            {
                "name": "zoho",
                "display_name": "Zoho Desk",
                "connection_types": ["webhook", "api_poll"],
                "description": "Zoho Desk ticketing platform"
            }
        ]
    }



