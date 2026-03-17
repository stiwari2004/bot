"""
Mixin: authentication helpers for ServiceNowTicketFetcher
"""
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceNowAuthMixin:
    """Authentication helpers for ServiceNowTicketFetcher."""

    async def _get_auth_headers(
        self,
        api_base_url: str,
        connection_meta: Dict[str, Any],
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Dict[str, str]:
        """Get authentication headers (OAuth 2.0 or Basic Auth)"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logger.info(f"ServiceNow auth - username param: {'present' if username else 'missing'}, password param: {'present' if password else 'missing'}")
        logger.info(f"ServiceNow auth - client_id: {'present' if client_id else 'missing'}, client_secret: {'present' if client_secret else 'missing'}")
        logger.info(f"ServiceNow auth - connection_meta keys: {list(connection_meta.keys())}")
        logger.info(f"ServiceNow auth - meta username: {'present' if connection_meta.get('username') else 'missing'}, meta password: {'present' if connection_meta.get('password') else 'missing'}")

        if client_id and client_secret:
            try:
                access_token = await self._get_oauth_token(
                    api_base_url=api_base_url,
                    connection_meta=connection_meta,
                    client_id=client_id,
                    client_secret=client_secret
                )
                if access_token:
                    headers["Authorization"] = f"Bearer {access_token}"
                    logger.info("Using ServiceNow OAuth 2.0 authentication")
                    return headers
            except Exception as e:
                logger.warning(f"OAuth authentication failed, falling back to Basic Auth: {e}")

        if username and password:
            if username.strip() and password.strip():
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
                logger.info(f"Using ServiceNow Basic Auth from parameters (username: {username[:3]}...)")
                logger.debug(f"Basic Auth header set: Authorization=Basic {encoded[:20]}... (length: {len(encoded)})")
                return headers
            else:
                logger.warning("Username/password parameters provided but are empty strings")

        meta_username = connection_meta.get("username")
        meta_password = connection_meta.get("password")
        logger.debug(f"Checking connection_meta for credentials: username={'present' if meta_username else 'missing'}, password={'present' if meta_password else 'missing'}")

        if meta_username and meta_password:
            if isinstance(meta_username, str) and isinstance(meta_password, str):
                if meta_username.strip() and meta_password.strip():
                    credentials = f"{meta_username}:{meta_password}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers["Authorization"] = f"Basic {encoded}"
                    logger.info(f"Using ServiceNow Basic Auth from connection metadata (username: {meta_username[:3]}...)")
                    logger.debug(f"Basic Auth header set: Authorization=Basic {encoded[:20]}... (length: {len(encoded)})")
                    return headers
                else:
                    logger.warning("Meta username/password found but are empty strings")
            else:
                logger.warning(f"Meta username/password are not strings: username type={type(meta_username)}, password type={type(meta_password)}")

        logger.error(f"No valid authentication credentials found. Username param: {bool(username)}, Password param: {bool(password)}, Meta username: {bool(meta_username)}, Meta password: {bool(meta_password)}")
        logger.error(f"Username param value: {repr(username) if username else 'None'}, Password param value: {'***' if password else 'None'}")
        logger.error(f"Meta username value: {repr(meta_username) if meta_username else 'None'}, Meta password value: {'***' if meta_password else 'None'}")
        raise Exception("No valid authentication credentials provided for ServiceNow")

    async def _get_oauth_token(
        self,
        api_base_url: str,
        connection_meta: Dict[str, Any],
        client_id: str,
        client_secret: str
    ) -> Optional[str]:
        """Get OAuth 2.0 access token from ServiceNow"""
        access_token = connection_meta.get("access_token")
        expires_at = connection_meta.get("expires_at")

        if access_token and expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00')) if isinstance(expires_at, str) else expires_at
            if isinstance(expires_dt, datetime):
                now = datetime.now(expires_dt.tzinfo) if expires_dt.tzinfo else datetime.now()
                if expires_dt > now:
                    logger.debug("Using cached ServiceNow OAuth token")
                    return access_token

        token_url = f"{api_base_url}/oauth_token.do"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }

        try:
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)

            if access_token:
                expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)).isoformat()
                connection_meta["access_token"] = access_token
                connection_meta["expires_at"] = expires_at
                logger.info(f"Obtained new ServiceNow OAuth token (expires in {expires_in}s)")
                return access_token
        except Exception as e:
            logger.error(f"Failed to get ServiceNow OAuth token: {e}")
            return None

        return None
