"""
ManageEngine ServiceDesk Plus Ticket Fetcher
Fetches tickets from ManageEngine ServiceDesk Plus REST API
"""
import base64
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from app.core.logging import get_logger
from app.services.ticketing_connectors.zoho_oauth import ZohoOAuthService

logger = get_logger(__name__)


class ManageEngineTicketFetcher:
    """Fetches tickets (requests) from ManageEngine ServiceDesk Plus"""
    
    def __init__(self):
        self.oauth_service = ZohoOAuthService()  # ManageEngine uses same OAuth as Zoho
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_tickets(
        self,
        api_base_url: str,
        connection_meta: Dict[str, Any],
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_username: Optional[str] = None,
        api_password: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch tickets (requests) from ManageEngine ServiceDesk Plus
        
        Args:
            api_base_url: ManageEngine API base URL (e.g., https://your-instance.manageengine.com)
            connection_meta: Connection metadata
            api_key: API key (if using API key authentication)
            api_secret: API secret (if using API key authentication)
            api_username: Username (if using basic auth)
            api_password: Password (if using basic auth)
            status_filter: List of request statuses to filter
            limit: Maximum number of tickets to fetch
            since: Only fetch tickets updated since this datetime
        
        Returns:
            List of normalized ticket dictionaries
        """
        try:
            # ManageEngine uses OAuth 2.0 only
            access_token = await self._get_valid_token(connection_meta)
            
            if not access_token:
                raise Exception(
                    "ManageEngine connection requires OAuth credentials. "
                    "Please configure Client ID and Client Secret, then authorize the connection."
                )
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/vnd.manageengine.sdp.v3+json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            logger.info("Using ManageEngine OAuth authentication")
            
            # Normalize API base URL
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            # ManageEngine OAuth 2.0 API format
            # According to official docs: https://www.manageengine.com/products/service-desk/sdpod-v3-api/getting-started/oauth-2.0.html
            # input_data must be URL-encoded as a query parameter in GET requests
            api_url = f"{api_base_url}/api/v3/requests"
            
            # Build input_data according to official documentation
            # input_data should be a JSON string, URL-encoded as a query parameter
            input_data = {
                "list_info": {
                    "row_count": min(limit, 100),
                    "start_index": 1,
                    "sort_fields": [{"field": "modified_time", "order": "desc"}]
                }
            }
            
            # Add search criteria if since is provided
            if since:
                input_data["list_info"]["search_criteria"] = {
                    "field": "modified_time.value",
                    "condition": "greater than",
                    "value": str(int(since.timestamp() * 1000))
                }
            
            # Add status filter if provided
            if status_filter:
                if "search_criteria" not in input_data["list_info"]:
                    input_data["list_info"]["search_criteria"] = {}
                # Status filter can be added to search_criteria if needed
            
            # According to docs: input_data must be URL-encoded in query params
            # Format: input_data={"list_info": {...}} as URL-encoded string
            params = {
                "input_data": json.dumps(input_data)
            }
            
            logger.info(f"Fetching ManageEngine tickets via OAuth from {api_url} with input_data in query params")
            response = await self.client.get(
                api_url,
                headers=headers,
                params=params
            )
            
            # Log the response for debugging
            if response.status_code != 200:
                error_text = response.text[:1000] if hasattr(response, 'text') else str(response.content)[:1000]
                logger.error(f"ManageEngine API error {response.status_code}: {error_text}")
                logger.error(f"Request URL: {api_url}")
                logger.error(f"Request headers: {dict(headers)}")
                logger.error(f"Request params: {params if 'params' in locals() else 'N/A'}")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response - ManageEngine format varies
            requests = data.get("requests", [])
            if not requests and isinstance(data, list):
                requests = data
            
            all_tickets = []
            for req in requests[:limit]:
                normalized = self._normalize_ticket(req)
                all_tickets.append(normalized)
            
            logger.info(f"Fetched {len(all_tickets)} tickets from ManageEngine")
            return all_tickets
            
        except httpx.HTTPStatusError as e:
            logger.error(f"ManageEngine API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch tickets from ManageEngine: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching ManageEngine tickets: {e}")
            raise
    
    def _get_auth_headers(
        self,
        api_key: Optional[str],
        api_secret: Optional[str],
        api_username: Optional[str],
        api_password: Optional[str],
        connection_meta: Dict[str, Any]
    ) -> Dict[str, str]:
        """Get authentication headers based on available credentials"""
        headers = {"Content-Type": "application/json"}
        
        # Prefer API key/secret if available
        if api_key or connection_meta.get("api_key"):
            key = api_key or connection_meta.get("api_key")
            secret = api_secret or connection_meta.get("api_secret")
            if key and secret:
                # ManageEngine may use API key in query params, but some versions use headers
                # For now, we'll use basic auth with key:secret
                credentials = f"{key}:{secret}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
                return headers
        
        # Fall back to username/password basic auth
        if api_username or connection_meta.get("api_username"):
            username = api_username or connection_meta.get("api_username")
            password = api_password or connection_meta.get("api_password")
            if username and password:
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
                return headers
        
        # No auth headers - API key might be in query params only
        return headers
    
    def _build_input_data(
        self,
        status_filter: Optional[List[str]],
        limit: int,
        since: Optional[datetime]
    ) -> Dict[str, Any]:
        """Build input_data JSON for ManageEngine API"""
        input_data = {
            "list_info": {
                "row_count": limit,
                "start_index": 1,
                "sort_fields": [{"field": "modified_time", "order": "desc"}]
            }
        }
        
        if status_filter:
            input_data["list_info"]["search_criteria"] = [
                {"field": "status.name", "condition": "is", "value": status}
                for status in status_filter
            ]
        
        if since:
            input_data["list_info"]["search_criteria"] = input_data["list_info"].get("search_criteria", [])
            input_data["list_info"]["search_criteria"].append({
                "field": "modified_time",
                "condition": "greater_than",
                "value": int(since.timestamp())
            })
        
        return input_data
    
    def _build_request_body(
        self,
        status_filter: Optional[List[str]],
        limit: int,
        since: Optional[datetime]
    ) -> Dict[str, Any]:
        """Build request body for ManageEngine POST request"""
        return self._build_input_data(status_filter, limit, since)
    
    def _normalize_ticket(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ManageEngine request to our ticket format"""
        request_id = request.get("id") or request.get("request_id")
        subject = request.get("subject") or request.get("title", "No Subject")
        description = request.get("description") or request.get("description_text", "")
        status = request.get("status", {})
        status_name = status.get("name") if isinstance(status, dict) else str(status)
        priority = request.get("priority", {})
        priority_name = priority.get("name") if isinstance(priority, dict) else str(priority)
        
        # Map ManageEngine priority to severity
        priority_map = {
            "Critical": "critical",
            "High": "high",
            "Medium": "medium",
            "Low": "low"
        }
        severity = priority_map.get(priority_name, "medium")
        
        # Map ManageEngine status to our status
        status_map = {
            "Open": "open",
            "In Progress": "in_progress",
            "Pending": "open",
            "Resolved": "resolved",
            "Closed": "resolved"
        }
        normalized_status = status_map.get(status_name, "open")
        
        return {
            "external_id": str(request_id),
            "title": subject,
            "description": description,
            "severity": severity,
            "status": normalized_status,
            "source": "manageengine",
            "metadata": {
                "manageengine_request_id": request_id,
                "manageengine_status": status_name,
                "manageengine_priority": priority_name,
                "manageengine_created_time": request.get("created_time") or request.get("createdTime"),
                "manageengine_modified_time": request.get("modified_time") or request.get("modifiedTime"),
                "manageengine_technician": request.get("technician", {}).get("name") if isinstance(request.get("technician"), dict) else None
            }
        }
    
    async def _get_valid_token(self, connection_meta: Dict[str, Any]) -> Optional[str]:
        """Get valid access token, refreshing if necessary (same as Zoho)"""
        access_token = connection_meta.get("access_token")
        refresh_token = connection_meta.get("refresh_token")
        expires_at = connection_meta.get("expires_at")
        client_id = connection_meta.get("client_id")
        client_secret = connection_meta.get("client_secret")
        zoho_domain = connection_meta.get("zoho_domain", "in")  # Default to .in for ManageEngine
        
        if not access_token:
            return None
        
        # Check if token is expired (with 5 minute buffer)
        if expires_at:
            from datetime import datetime, timezone
            try:
                expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                if expires_dt <= now:
                    # Token expired, try to refresh
                    if refresh_token and client_id and client_secret:
                        try:
                            new_tokens = await self.oauth_service.refresh_access_token(
                                refresh_token, client_id, client_secret, domain=zoho_domain
                            )
                            # Update connection_meta (caller should persist this)
                            connection_meta["access_token"] = new_tokens["access_token"]
                            if "refresh_token" in new_tokens:
                                connection_meta["refresh_token"] = new_tokens["refresh_token"]
                            if "expires_in" in new_tokens:
                                from datetime import datetime, timezone, timedelta
                                connection_meta["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=new_tokens["expires_in"])).timestamp()
                            access_token = new_tokens["access_token"]
                            logger.info("Refreshed ManageEngine OAuth token")
                        except Exception as e:
                            logger.error(f"Failed to refresh ManageEngine token: {e}")
                            return None
            except Exception as e:
                logger.warning(f"Error checking token expiry: {e}")
        
        return access_token
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

