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
    
    ZOHO_AUTH_URL = "https://accounts.zoho.com/oauth/v2/auth"
    ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
    ZOHO_REFRESH_URL = "https://accounts.zoho.com/oauth/v2/token"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def generate_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: list = None,
        state: Optional[str] = None
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
        
        url = f"{self.ZOHO_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return url
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
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
            
            response = await self.client.post(
                self.ZOHO_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            # Log raw response for debugging
            response_text = response.text
            logger.info(f"Zoho token response status: {response.status_code}")
            logger.info(f"Zoho token response text (first 200 chars): {response_text[:200]}")
            
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
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if not access_token:
                logger.error(f"Zoho token response missing access_token! Full response: {token_data}")
                raise Exception("Zoho did not return an access_token in the response")
            
            logger.info(f"Successfully extracted access_token (length: {len(access_token) if access_token else 0}), refresh_token: {bool(refresh_token)}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
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
        client_secret: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Zoho refresh token
            client_id: Zoho OAuth client ID
            client_secret: Zoho OAuth client secret
        
        Returns:
            Dictionary with new access_token, expires_in, etc.
        """
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
            
            response = await self.client.post(
                self.ZOHO_REFRESH_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                "access_token": token_data.get("access_token"),
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "token_type": token_data.get("token_type", "Bearer"),
                "api_domain": token_data.get("api_domain", "https://desk.zoho.com")
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh token: {e.response.text}")
            raise Exception(f"Token refresh failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
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

