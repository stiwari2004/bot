"""
ManageEngine ServiceDesk Plus Ticket Fetcher
Fetches tickets from ManageEngine ServiceDesk Plus REST API
"""
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class ManageEngineTicketFetcher:
    """Fetches tickets (requests) from ManageEngine ServiceDesk Plus"""
    
    def __init__(self):
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
            # Determine authentication method
            headers = self._get_auth_headers(
                api_key, api_secret, api_username, api_password, connection_meta
            )
            
            # Normalize API base URL
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            # Build API URL - ManageEngine uses /api/v3/requests
            api_url = f"{api_base_url}/api/v3/requests"
            
            # Build query parameters
            params = {
                "TECHNICIAN_KEY": api_key or connection_meta.get("api_key", ""),
                "input_data": self._build_input_data(status_filter, limit, since)
            }
            
            # ManageEngine ServiceDesk Plus API - try GET first (simpler)
            # GET request with TECHNICIAN_KEY in params
            tech_key = api_key or connection_meta.get("api_key") or connection_meta.get("api_username")
            
            response = await self.client.get(
                api_url,
                headers=headers,
                params={
                    "TECHNICIAN_KEY": tech_key or "",
                    "limit": limit
                }
            )
            
            # If GET fails with 400/405/404, try POST
            if response.status_code in (400, 405, 404):
                logger.info(f"GET failed with {response.status_code}, trying POST...")
                request_body = self._build_request_body(status_filter, limit, since)
                response = await self.client.post(
                    api_url,
                    headers=headers,
                    params={"TECHNICIAN_KEY": tech_key or ""},
                    json=request_body
                )
            
            # Log the response for debugging
            if response.status_code != 200:
                logger.error(f"ManageEngine API error {response.status_code}: {response.text[:500]}")
            
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
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

