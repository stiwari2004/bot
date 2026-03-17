"""
Mixin: ticketing connection OAuth authorization operations
"""
import json
import secrets
from typing import Optional
from urllib.parse import urlencode

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ticketing_connectors.zoho_oauth import ZohoOAuthService

logger = get_logger(__name__)
_oauth_service = ZohoOAuthService()


class TicketingConnectionOAuthMixin:
    """OAuth authorization operations for TicketingConnectionController."""

    def build_oauth_authorize_url(self, connection_id: int, method: str = "POST") -> dict:
        connection = self._fetch(connection_id)
        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")

        meta_data = self._parse_meta_data(connection.meta_data)
        if connection.tool_name == "manageengine":
            if str(meta_data.get("version", "v2")).lower() == "v3":
                raise HTTPException(status_code=400, detail="OAuth is not supported for ManageEngine v3 (API key) connections.")

        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL

        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials (client_id, client_secret) not configured")

        state_token = f"{connection_id}:{secrets.token_urlsafe(32)}"
        zoho_domain = meta_data.get("zoho_domain", "in") if connection.tool_name == "manageengine" else "com"
        scope = (
            "SDPOnDemand.requests.ALL,SDPOnDemand.general.READ"
            if connection.tool_name == "manageengine"
            else "Desk.tickets.READ,Desk.tickets.WRITE,Desk.tickets.UPDATE"
        )

        params = {
            "scope": scope, "client_id": client_id, "response_type": "code",
            "redirect_uri": redirect_uri, "access_type": "offline", "state": state_token,
        }
        full_url = f"https://accounts.zoho.{zoho_domain}/oauth/v2/auth?{urlencode(params)}"
        return {"authorization_url": full_url, "state": state_token, "redirect_url": full_url}

    async def exchange_oauth_callback(self, connection_id: int, code: str, state: Optional[str] = None) -> dict:
        db = self.db
        connection = self._fetch(connection_id)
        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")

        meta_data = self._parse_meta_data(connection.meta_data)
        if connection.tool_name == "manageengine" and str(meta_data.get("version", "v2")).lower() == "v3":
            raise HTTPException(status_code=400, detail="OAuth is not supported for ManageEngine v3 connections.")

        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials not configured")

        zoho_domain = meta_data.get("zoho_domain", "in") if connection.tool_name == "manageengine" else "com"
        tokens = await _oauth_service.exchange_code_for_tokens(
            code=code, client_id=client_id, client_secret=client_secret,
            redirect_uri=redirect_uri, domain=zoho_domain,
        )
        meta_data.update(tokens)
        connection.meta_data = json.dumps(meta_data)
        db.commit()
        return {"status": "success", "message": "OAuth authorization successful", "connection_id": connection_id}

    async def handle_public_oauth_callback(self, code: str, state: Optional[str]):
        """Public (unauthenticated) OAuth callback — connection_id encoded in state as '<id>:<random>'."""
        db = self.db
        if not state or ":" not in state:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state. Please open the connection in Resolvify and click Authorize again.",
            )
        try:
            connection_id = int(state.split(":", 1)[0])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid connection_id in OAuth state")

        connection = self.connection_repo.get_by_id(connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        if connection.tool_name not in ("zoho", "manageengine"):
            raise HTTPException(status_code=400, detail=f"OAuth not supported for {connection.tool_name}")

        meta_data = self._parse_meta_data(connection.meta_data)
        if connection.tool_name == "manageengine" and str(meta_data.get("version", "v2")).lower() == "v3":
            raise HTTPException(status_code=400, detail="OAuth is not supported for ManageEngine v3 connections.")

        client_id = meta_data.get("client_id")
        client_secret = meta_data.get("client_secret")
        redirect_uri = meta_data.get("redirect_uri") or settings.OAUTH_CALLBACK_URL
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="OAuth credentials not configured")

        zoho_domain = meta_data.get("zoho_domain", "in") if connection.tool_name == "manageengine" else "com"
        try:
            tokens = await _oauth_service.exchange_code_for_tokens(
                code=code, client_id=client_id, client_secret=client_secret,
                redirect_uri=redirect_uri, domain=zoho_domain,
            )
        except Exception as token_err:
            raise HTTPException(
                status_code=400,
                detail=f"Authorization failed: {str(token_err)}. Check redirect URI and client credentials.",
            )

        meta_data.update(tokens)
        connection.meta_data = json.dumps(meta_data)
        db.commit()

        redirect_url = f"{settings.FRONTEND_BASE_URL}/?tab=settings&oauth_success=1&connection_id={connection_id}"
        return RedirectResponse(url=redirect_url, status_code=302)
