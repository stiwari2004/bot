"""
Zoho OAuth Service
Handles OAuth2 authorization flow for Zoho Desk API
"""
import secrets
import hashlib
import base64
import urllib.parse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class ZohoOAuthService:
    """Service for handling Zoho OAuth2 flow"""
    
    # Default to .com, but support .in for Indian accounts
    DEFAULT_DOMAIN = "com"
    AUTH_URL_TEMPLATE = "https://accounts.zoho.{domain}/oauth/v2/auth"
    TOKEN_URL_TEMPLATE = "https://accounts.zoho.{domain}/oauth/v2/token"
    
    def _get_domain(self, client_id: Optional[str] = None) -> str:
        """
        Determine Zoho domain based on client_id or default to .com
        For Indian accounts (api-console.zoho.in), use .in
        """
        # Check if client_id starts with specific patterns for Indian accounts
        # Indian accounts typically use api-console.zoho.in
        # For now, default to .com, but could be enhanced to detect from client_id
        # or allow it to be configured per connection
        return self.DEFAULT_DOMAIN
    
    def _get_auth_url(self, domain: Optional[str] = None) -> str:
        """Get authorization URL for the specified domain"""
        domain = domain or self._get_domain()
        return self.AUTH_URL_TEMPLATE.format(domain=domain)
    
    def _get_token_url(self, domain: Optional[str] = None) -> str:
        """Get token URL for the specified domain"""
        domain = domain or self._get_domain()
        return self.TOKEN_URL_TEMPLATE.format(domain=domain)
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def generate_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: list = None,
        state: Optional[str] = None,
        domain: Optional[str] = None
    ) -> str:
        """
        Generate OAuth2 authorization URL for Zoho
        
        Args:
            client_id: Zoho OAuth client ID
            redirect_uri: OAuth callback redirect URI
            scopes: List of OAuth scopes (default: Desk.tickets.READ)
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["Desk.tickets.READ", "Desk.tickets.CREATE", "Desk.tickets.UPDATE"]
        
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": client_id,
            "scope": ",".join(scopes),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "state": state
        }
        
        auth_url = self._get_auth_url(domain)
        url = f"{auth_url}?{urllib.parse.urlencode(params)}"
        return url
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from OAuth callback
            client_id: Zoho OAuth client ID
            client_secret: Zoho OAuth client secret
            redirect_uri: OAuth callback redirect URI
        
        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
            
            # Log request details (without secret)
            logger.info(f"Zoho token exchange request: client_id={client_id[:10]}..., redirect_uri={redirect_uri}, code={code[:20]}...")
            
            token_url = self._get_token_url(domain)
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Log response before raising
            response_text = response.text
            logger.info(f"Zoho token response status: {response.status_code}")
            logger.info(f"Zoho token response text (first 500 chars): {response_text[:500]}")
            
            # Check for errors before raising
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description") or error_data.get("error") or response_text
                    logger.error(f"Zoho OAuth token exchange failed: {error_msg}")
                    logger.error(f"Full error response: {error_data}")
                    raise Exception(f"Zoho OAuth error: {error_msg}")
                except:
                    logger.error(f"Zoho OAuth token exchange failed with status {response.status_code}: {response_text}")
                    raise Exception(f"Zoho OAuth error: HTTP {response.status_code} - {response_text[:200]}")
            
            response.raise_for_status()
            
            try:
                token_data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse Zoho response as JSON: {e}, Response: {response_text}")
                raise
            
            # Check for error in response (Zoho sometimes returns 200 with error in body)
            if "error" in token_data:
                error_msg = token_data.get("error_description") or token_data.get("error")
                logger.error(f"Zoho returned error in response: {error_msg}, Full response: {token_data}")
                raise Exception(f"Zoho OAuth error: {error_msg}")
            
            logger.info(f"Zoho token response keys: {list(token_data.keys())}")
            
            # Log FULL response for debugging (sanitize access_token but keep structure)
            sanitized_response = token_data.copy()
            if "access_token" in sanitized_response:
                sanitized_response["access_token"] = f"***{sanitized_response['access_token'][-10:]}" if len(sanitized_response["access_token"]) > 10 else "***"
            logger.info(f"Zoho token exchange FULL response (sanitized): {sanitized_response}")
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if not access_token:
                logger.error(f"Zoho token response missing access_token! Full response: {token_data}")
                raise Exception("Zoho did not return an access_token in the response")
            
            # Log detailed information about refresh_token
            if refresh_token:
                logger.info(f"✅ SUCCESS: Zoho returned refresh_token! access_token length: {len(access_token)}, refresh_token length: {len(refresh_token)}")
            else:
                logger.error(
                    f"❌ CRITICAL: Zoho did not return refresh_token in token exchange response! "
                    f"This will prevent automatic token refresh. Response keys: {list(token_data.keys())}, "
                    f"Full response (sanitized): {sanitized_response}"
                )
                # Don't fail, but log a warning - some OAuth apps may not issue refresh tokens
                # or user may have already authorized before
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,  # May be None if Zoho didn't return it
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "token_type": token_data.get("token_type", "Bearer"),
                "api_domain": token_data.get("api_domain", "https://desk.zoho.com")
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to exchange code for tokens: {e.response.text}")
            raise Exception(f"OAuth token exchange failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            raise
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        domain: Optional[str] = None,
        existing_refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        According to Zoho OAuth 2.0 documentation:
        - Refresh tokens do not expire and can be reused
        - Zoho may or may not return a new refresh_token in the refresh response
        - If a new refresh_token is returned, use it; otherwise, preserve the existing one
        
        Args:
            refresh_token: Zoho refresh token to use for refresh
            client_id: Zoho OAuth client ID
            client_secret: Zoho OAuth client secret
            domain: Zoho domain (com, in, etc.)
            existing_refresh_token: The existing refresh_token to preserve if Zoho doesn't return a new one
        
        Returns:
            Dictionary with new access_token, refresh_token (preserved or new), expires_in, etc.
        """
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
            
            refresh_url = self._get_token_url(domain)  # Refresh uses same URL as token
            logger.debug(f"Refreshing token via {refresh_url}")
            
            response = await self.client.post(
                refresh_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Check for errors in response (Zoho sometimes returns 200 with error in body)
            if "error" in token_data:
                error_msg = token_data.get("error_description") or token_data.get("error")
                logger.error(f"Zoho returned error in refresh response: {error_msg}, Full response: {token_data}")
                raise Exception(f"Zoho OAuth refresh error: {error_msg}")
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Handle refresh_token: Zoho may or may not return a new one
            # If Zoho returns a new refresh_token, use it; otherwise, preserve the existing one
            new_refresh_token = token_data.get("refresh_token")
            if not new_refresh_token:
                # Zoho didn't return a new refresh_token, preserve the existing one
                # Use the one passed as parameter (existing_refresh_token) or the one used for refresh
                preserved_refresh_token = existing_refresh_token or refresh_token
                logger.debug("Zoho did not return new refresh_token, preserving existing one")
            else:
                # Zoho returned a new refresh_token, use it
                preserved_refresh_token = new_refresh_token
                logger.debug("Zoho returned new refresh_token, using it")
            
            if not preserved_refresh_token:
                logger.warning("No refresh_token available to preserve - this may cause issues on next refresh")
            
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": preserved_refresh_token,  # Always include refresh_token
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "token_type": token_data.get("token_type", "Bearer"),
                "api_domain": token_data.get("api_domain", "https://desk.zoho.com")
            }
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e.response.content)
            logger.error(f"Failed to refresh token: HTTP {e.response.status_code} - {error_text}")
            raise Exception(f"Token refresh failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error refreshing token: {e}", exc_info=True)
            raise
    
    def is_token_expired(self, expires_at: Optional[str]) -> bool:
        """Check if token is expired"""
        if not expires_at:
            return True
        
        try:
            exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            # Add 5 minute buffer
            return datetime.utcnow() >= (exp_time - timedelta(minutes=5))
        except Exception:
            return True
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

