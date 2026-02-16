"""
ServiceNow Ticket Fetcher
Fetches incidents from ServiceNow using OAuth 2.0 or Basic Auth
"""
import base64
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceNowTicketFetcher:
    """Fetches incidents from ServiceNow"""
    
    def __init__(self):
        # Enable event hooks to log actual HTTP requests being sent
        async def log_request(request):
            logger.info(f"httpx REQUEST: {request.method} {request.url}")
            logger.info(f"httpx REQUEST HEADERS: {dict(request.headers)}")
            if 'Authorization' in request.headers:
                auth_val = request.headers['Authorization']
                logger.info(f"httpx Authorization header in request: {auth_val[:30]}...")
            else:
                logger.error("CRITICAL: Authorization header MISSING in httpx request!")
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            event_hooks={'request': [log_request]}
        )
    
    async def fetch_tickets(
        self,
        api_base_url: str,
        connection_meta: Dict[str, Any],
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch incidents from ServiceNow
        
        Args:
            api_base_url: ServiceNow instance URL (e.g., https://your-instance.service-now.com)
            connection_meta: Connection metadata containing auth tokens
            username: Username for Basic Auth (optional)
            password: Password for Basic Auth (optional)
            client_id: OAuth client ID (optional)
            client_secret: OAuth client secret (optional)
            status_filter: List of incident states to filter (e.g., ['1', '2'] for New, In Progress)
            limit: Maximum number of incidents to fetch
            since: Only fetch incidents updated since this datetime
        
        Returns:
            List of normalized ticket dictionaries
        """
        try:
            # Normalize API base URL
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            # Get authentication headers
            # Use provided username/password, or fall back to connection_meta
            # Handle empty strings by treating them as None
            final_username = username if username and username.strip() else connection_meta.get("username")
            final_password = password if password and password.strip() else connection_meta.get("password")
            final_client_id = client_id if client_id and client_id.strip() else connection_meta.get("client_id")
            final_client_secret = client_secret if client_secret and client_secret.strip() else connection_meta.get("client_secret")
            
            logger.info(f"ServiceNow fetch_tickets - final credentials: username={'present' if final_username else 'missing'}, password={'present' if final_password else 'missing'}")
            logger.info(f"ServiceNow connection_meta keys: {list(connection_meta.keys())}")
            if final_username:
                logger.info(f"ServiceNow username value: {final_username[:10]}... (length: {len(final_username)})")
            if final_password:
                logger.info(f"ServiceNow password length: {len(final_password)} chars, first 5 chars: {final_password[:5]}...")
            
            # Get Basic Auth credentials - use the FINAL credentials directly
            basic_auth_username = None
            basic_auth_password = None
            
            if final_username and final_password and final_username.strip() and final_password.strip():
                basic_auth_username = final_username.strip()
                basic_auth_password = final_password.strip()
                logger.info(f"✅ Using credentials from parameters: username length={len(basic_auth_username)}, password length={len(basic_auth_password)}")
            elif connection_meta.get("username") and connection_meta.get("password"):
                meta_user = connection_meta.get("username")
                meta_pass = connection_meta.get("password")
                logger.info(f"Found credentials in meta_data: username type={type(meta_user).__name__}, password type={type(meta_pass).__name__}")
                if isinstance(meta_user, str) and isinstance(meta_pass, str) and meta_user.strip() and meta_pass.strip():
                    basic_auth_username = meta_user.strip()
                    basic_auth_password = meta_pass.strip()
                    logger.info(f"✅ Using credentials from meta_data: username length={len(basic_auth_username)}, password length={len(basic_auth_password)}")
                else:
                    logger.warning(f"⚠️ Meta credentials exist but invalid: username is_str={isinstance(meta_user, str)}, password is_str={isinstance(meta_pass, str)}, username empty={not meta_user.strip() if isinstance(meta_user, str) else 'N/A'}, password empty={not meta_pass.strip() if isinstance(meta_pass, str) else 'N/A'}")
            else:
                logger.warning(f"⚠️ No credentials in connection_meta: username={'present' if connection_meta.get('username') else 'missing'}, password={'present' if connection_meta.get('password') else 'missing'}")
            
            if basic_auth_username and basic_auth_password:
                # Build headers from scratch - don't use _get_auth_headers which might have issues
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # HTTP Basic Auth REQUIRES base64 encoding (RFC 7617)
                # Postman automatically base64-encodes when you select "Basic Auth"
                credentials = f"{basic_auth_username}:{basic_auth_password}"
                logger.info(f"Credentials string (first 20 chars): {credentials[:20]}... (full length: {len(credentials)})")
                encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                auth_header = f"Basic {encoded}"
                headers["Authorization"] = auth_header
                logger.info(f"Authorization header (base64 encoded): {auth_header[:50]}... (full length: {len(auth_header)})")
                logger.info(f"Username: {basic_auth_username}, Password length: {len(basic_auth_password)} chars")
                logger.info(f"Base64 encoded value: {encoded[:50]}... (full length: {len(encoded)})")
                auth = None  # Don't use httpx BasicAuth - using manual header
            else:
                logger.error(f"❌ CRITICAL: No credentials found! Username: {bool(basic_auth_username)}, Password: {bool(basic_auth_password)}")
                logger.error(f"   final_username: {bool(final_username)}, final_password: {bool(final_password)}")
                logger.error(f"   connection_meta.username: {bool(connection_meta.get('username'))}, connection_meta.password: {bool(connection_meta.get('password'))}")
                logger.error(f"   This connection needs username/password set via API or UI")
                auth = None
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                # Don't make request without credentials - raise immediately
                raise ValueError(
                    "ServiceNow credentials (username/password) are required for Basic Auth. "
                    "Please update the connection with valid ServiceNow username and password."
                )
            
            # ServiceNow API endpoint for incidents
            api_url = f"{api_base_url}/api/now/table/incident"
            
            # Build query parameters
            params = {
                "sysparm_limit": min(limit, 100),  # ServiceNow max is 100 per page
                "sysparm_orderby": "sys_updated_on:desc",
                "sysparm_display_value": "true"  # Return display values
            }
            
            # Add status filter if provided
            if status_filter:
                # ServiceNow states: 1=New, 2=In Progress, 3=On Hold, 4=Resolved, 5=Closed, 6=Canceled
                params["sysparm_query"] = f"stateIN{','.join(status_filter)}"
            
            # Add updated since filter
            if since:
                # ServiceNow accepts date-only format: YYYY-MM-DD (no time component)
                # Convert to UTC if not already timezone-aware
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
                # Format as date-only (YYYY-MM-DD) - ServiceNow accepts this format
                since_str = since.strftime("%Y-%m-%d")
                # Query for tickets that were EITHER created OR updated since last sync
                # This catches new tickets (created) and updated tickets (updated)
                # ServiceNow OR syntax: field1=value1^ORfield2=value2 (no ^ before OR, no parentheses)
                query_filter = f"sys_created_on>={since_str}^ORsys_updated_on>={since_str}"
                if "sysparm_query" in params:
                    params["sysparm_query"] += f"^{query_filter}"
                else:
                    params["sysparm_query"] = query_filter
                logger.info(f"ServiceNow query filter: {query_filter} (since={since}, date-only format)")
            else:
                logger.info("ServiceNow query: No date filter (fetching all recent tickets)")
            
            logger.info(f"ServiceNow API URL: {api_url}")
            logger.info(f"ServiceNow query params: {params}")
            
            all_tickets = []
            offset = 0
            
            while len(all_tickets) < limit:
                params["sysparm_offset"] = offset
                
                logger.debug(f"Fetching ServiceNow incidents: offset={offset}, limit={params['sysparm_limit']}")
                logger.info(f"Request headers keys: {list(headers.keys())}")
                logger.info(f"Authorization header present: {'YES' if 'Authorization' in headers else 'NO'}")
                if 'Authorization' in headers:
                    auth_header_value = headers['Authorization']
                    logger.info(f"Authorization header value: {auth_header_value[:30]}... (length: {len(auth_header_value)})")
                else:
                    logger.error("CRITICAL: Authorization header is MISSING from headers dict!")
                
                # Use ONLY manual header (exactly like Postman)
                # Don't use httpx BasicAuth - it might conflict or not work correctly
                response = await self.client.get(
                    api_url,
                    headers=headers,
                    params=params
                    # NO auth parameter - using manual Authorization header only
                )
                # Log response to debug
                logger.info(f"Response status: {response.status_code}")
                if response.status_code == 401:
                    logger.error(f"401 Response body: {response.text[:200]}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                logger.debug(f"ServiceNow API response status: {response.status_code}")
                
                # Check Content-Type header
                content_type = response.headers.get("Content-Type", "").lower()
                response_text = response.text
                
                # Check if ServiceNow instance is hibernated (returns HTML instead of JSON)
                if "text/html" in content_type or (response_text and response_text.strip().startswith("<html")):
                    if "hibernat" in response_text.lower() or "Instance Hibernating" in response_text:
                        logger.warning(f"ServiceNow instance appears to be hibernated (returned HTML hibernation page)")
                        logger.warning(f"Response preview: {response_text[:200]}")
                        raise Exception(
                            "ServiceNow instance is hibernated. "
                            "Developer instances hibernate after inactivity. "
                            "Please wake up your ServiceNow instance by accessing it in a browser, "
                            "then try again in a few minutes."
                        )
                    else:
                        logger.warning(f"ServiceNow returned HTML instead of JSON (status: {response.status_code})")
                        logger.warning(f"Response preview: {response_text[:200]}")
                        raise Exception(
                            f"ServiceNow API returned HTML instead of JSON (status: {response.status_code}). "
                            "This may indicate the instance is hibernated or the API endpoint is incorrect."
                        )
                
                # Check if response has content before parsing JSON
                if not response_text or not response_text.strip():
                    logger.error(f"ServiceNow API returned empty response (status: {response.status_code})")
                    raise Exception(f"ServiceNow API returned empty response (status: {response.status_code})")
                
                # Raise for status after content checks (to get better error messages)
                response.raise_for_status()
                
                try:
                    data = response.json()
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to parse ServiceNow JSON response: {e}")
                    logger.error(f"Content-Type: {content_type}")
                    logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                    # Check if it's HTML that we missed
                    if response_text.strip().startswith("<"):
                        raise Exception(
                            "ServiceNow API returned HTML instead of JSON. "
                            "This may indicate the instance is hibernated or the API endpoint is incorrect."
                        )
                    raise Exception(f"ServiceNow API returned invalid JSON: {str(e)}")
                
                incidents = data.get("result", [])
                
                logger.info(f"ServiceNow API returned {len(incidents)} incidents (offset={offset})")
                
                if not incidents:
                    logger.info("No more incidents from ServiceNow API")
                    break
                
                # Normalize incidents
                for incident in incidents:
                    normalized = self._normalize_ticket(incident)
                    all_tickets.append(normalized)
                    logger.debug(f"Normalized ServiceNow incident: {normalized.get('external_id')} - {normalized.get('title')}")
                
                # Check if there are more pages
                if len(incidents) < params["sysparm_limit"] or len(all_tickets) >= limit:
                    break
                
                offset += len(incidents)
            
            logger.info(f"Fetched {len(all_tickets)} incidents from ServiceNow (normalized)")
            if all_tickets:
                logger.info(f"Sample incident IDs: {[t.get('external_id') for t in all_tickets[:5]]}")
            return all_tickets[:limit]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"ServiceNow API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch incidents from ServiceNow: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching ServiceNow incidents: {e}")
            raise
    
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
        
        # Log what we received for debugging
        logger.info(f"ServiceNow auth - username param: {'present' if username else 'missing'}, password param: {'present' if password else 'missing'}")
        logger.info(f"ServiceNow auth - client_id: {'present' if client_id else 'missing'}, client_secret: {'present' if client_secret else 'missing'}")
        logger.info(f"ServiceNow auth - connection_meta keys: {list(connection_meta.keys())}")
        logger.info(f"ServiceNow auth - meta username: {'present' if connection_meta.get('username') else 'missing'}, meta password: {'present' if connection_meta.get('password') else 'missing'}")
        
        # Try OAuth 2.0 first if client_id and client_secret are provided
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
        
        # Fall back to Basic Auth - check username/password parameters first
        if username and password:
            # Check if they're not empty strings
            if username.strip() and password.strip():
                credentials = f"{username}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
                logger.info(f"Using ServiceNow Basic Auth from parameters (username: {username[:3]}...)")
                logger.debug(f"Basic Auth header set: Authorization=Basic {encoded[:20]}... (length: {len(encoded)})")
                return headers
            else:
                logger.warning("Username/password parameters provided but are empty strings")
        
        # Try to get credentials from connection_meta
        meta_username = connection_meta.get("username")
        meta_password = connection_meta.get("password")
        logger.debug(f"Checking connection_meta for credentials: username={'present' if meta_username else 'missing'}, password={'present' if meta_password else 'missing'}")
        
        if meta_username and meta_password:
            # Check if they're not empty strings
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
        # Check if we have a valid cached token
        access_token = connection_meta.get("access_token")
        expires_at = connection_meta.get("expires_at")
        
        if access_token and expires_at:
            # Check if token is still valid (with 5 minute buffer)
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00')) if isinstance(expires_at, str) else expires_at
            if isinstance(expires_dt, datetime):
                now = datetime.now(expires_dt.tzinfo) if expires_dt.tzinfo else datetime.now()
                if expires_dt > now:
                    logger.debug("Using cached ServiceNow OAuth token")
                    return access_token
        
        # Get new token
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
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            
            if access_token:
                # Calculate expiration time
                from datetime import timedelta, timezone
                expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)).isoformat()  # 5 min buffer
                
                # Update connection_meta (caller should persist this)
                connection_meta["access_token"] = access_token
                connection_meta["expires_at"] = expires_at
                
                logger.info(f"Obtained new ServiceNow OAuth token (expires in {expires_in}s)")
                return access_token
        except Exception as e:
            logger.error(f"Failed to get ServiceNow OAuth token: {e}")
            return None
        
        return None
    
    def _normalize_ticket(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize ServiceNow incident to our ticket format"""
        sys_id = incident.get("sys_id")
        number = incident.get("number")
        short_description = incident.get("short_description", "No Subject")
        description = incident.get("description", "")
        state = incident.get("state", "1")
        urgency = incident.get("urgency", "3")
        impact = incident.get("impact", "3")
        priority = incident.get("priority", "3")
        
        # Map ServiceNow state to our status
        # ServiceNow states: 1=New, 2=In Progress, 3=On Hold, 4=Resolved, 5=Closed, 6=Canceled
        state_map = {
            "1": "open",  # New
            "2": "in_progress",  # In Progress
            "3": "open",  # On Hold
            "4": "resolved",  # Resolved
            "5": "resolved",  # Closed
            "6": "resolved"  # Canceled
        }
        normalized_status = state_map.get(str(state), "open")
        
        # Map ServiceNow priority/urgency to severity
        # ServiceNow priority: 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning
        priority_map = {
            "1": "critical",  # Critical
            "2": "high",  # High
            "3": "medium",  # Moderate
            "4": "low",  # Low
            "5": "low"  # Planning
        }
        severity = priority_map.get(str(priority), "medium")
        
        # If priority is not set, use urgency
        if severity == "medium" and urgency:
            urgency_map = {
                "1": "critical",  # Critical
                "2": "high",  # High
                "3": "medium",  # Medium
                "4": "low",  # Low
                "5": "low"  # Planning
            }
            severity = urgency_map.get(str(urgency), "medium")
        
        return {
            "external_id": str(number or sys_id),  # Use number if available, fallback to sys_id
            "title": short_description,
            "description": description,
            "severity": severity,
            "status": normalized_status,
            "source": "servicenow",
            "metadata": {
                "servicenow_sys_id": sys_id,
                "servicenow_number": number,
                "servicenow_state": state,
                "servicenow_urgency": urgency,
                "servicenow_impact": impact,
                "servicenow_priority": priority,
                "servicenow_created_time": incident.get("sys_created_on"),
                "servicenow_updated_time": incident.get("sys_updated_on"),
                "servicenow_assigned_to": incident.get("assigned_to", {}).get("display_value") if isinstance(incident.get("assigned_to"), dict) else incident.get("assigned_to"),
                "servicenow_caller": incident.get("caller_id", {}).get("display_value") if isinstance(incident.get("caller_id"), dict) else incident.get("caller_id")
            }
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

