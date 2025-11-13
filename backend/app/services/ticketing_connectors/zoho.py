"""
Zoho Desk Ticket Fetcher
Fetches tickets from Zoho Desk API using OAuth2 authentication
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from app.core.logging import get_logger
from app.services.ticketing_connectors.zoho_oauth import ZohoOAuthService

logger = get_logger(__name__)


class ZohoTicketFetcher:
    """Fetches tickets from Zoho Desk"""
    
    def __init__(self):
        self.oauth_service = ZohoOAuthService()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_tickets(
        self,
        connection_meta: Dict[str, Any],
        api_base_url: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch tickets from Zoho Desk
        
        Args:
            connection_meta: Connection metadata containing OAuth tokens
            api_base_url: Zoho Desk API base URL (optional, from meta or default)
            status_filter: List of ticket statuses to filter (e.g., ['Open', 'In Progress'])
            limit: Maximum number of tickets to fetch
            since: Only fetch tickets updated since this datetime
        
        Returns:
            List of normalized ticket dictionaries
        """
        try:
            # Get access token, refresh if needed
            access_token = await self._get_valid_token(connection_meta)
            if not access_token:
                raise Exception("Failed to obtain valid access token")
            
            # Determine API base URL
            api_domain = connection_meta.get("api_domain", "https://desk.zoho.com")
            if api_base_url:
                api_domain = api_base_url
            elif not api_domain.startswith("http"):
                api_domain = f"https://{api_domain}"
            
            # Build API URL
            org_id = connection_meta.get("org_id")
            if not org_id:
                # Try to get org ID from API
                org_id = await self._get_org_id(api_domain, access_token)
            
            api_url = f"{api_domain}/api/v1/tickets"
            
            # Build query parameters
            params = {
                "limit": min(limit, 100),  # Zoho max is 100 per page
                "sortBy": "modifiedTime",
                "sortOrder": "desc"
            }
            
            if status_filter:
                params["status"] = ",".join(status_filter)
            
            if since:
                # Zoho uses epoch time in milliseconds
                params["modifiedSince"] = int(since.timestamp() * 1000)
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            all_tickets = []
            page = 1
            
            while len(all_tickets) < limit:
                params["page"] = page
                response = await self.client.get(api_url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                tickets = data.get("data", [])
                
                if not tickets:
                    break
                
                # Normalize tickets
                for ticket in tickets:
                    normalized = self._normalize_ticket(ticket, org_id)
                    all_tickets.append(normalized)
                
                # Check if there are more pages
                if len(tickets) < params["limit"] or len(all_tickets) >= limit:
                    break
                
                page += 1
            
            logger.info(f"Fetched {len(all_tickets)} tickets from Zoho Desk")
            return all_tickets[:limit]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Zoho API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch tickets from Zoho: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching Zoho tickets: {e}")
            raise
    
    async def _get_org_id(self, api_domain: str, access_token: str) -> Optional[str]:
        """Get organization ID from Zoho Desk"""
        try:
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            response = await self.client.get(
                f"{api_domain}/api/v1/organizations",
                headers=headers,
                params={"limit": 1}
            )
            response.raise_for_status()
            data = response.json()
            orgs = data.get("data", [])
            if orgs:
                return orgs[0].get("id")
        except Exception as e:
            logger.warning(f"Could not fetch org ID: {e}")
        return None
    
    async def _get_valid_token(self, connection_meta: Dict[str, Any]) -> Optional[str]:
        """Get valid access token, refreshing if necessary"""
        access_token = connection_meta.get("access_token")
        refresh_token = connection_meta.get("refresh_token")
        expires_at = connection_meta.get("expires_at")
        client_id = connection_meta.get("client_id")
        client_secret = connection_meta.get("client_secret")
        
        if not access_token:
            return None
        
        # Check if token is expired
        if self.oauth_service.is_token_expired(expires_at):
            if refresh_token and client_id and client_secret:
                try:
                    logger.info("Refreshing Zoho access token")
                    new_tokens = await self.oauth_service.refresh_access_token(
                        refresh_token, client_id, client_secret
                    )
                    # Update connection_meta (caller should persist this)
                    connection_meta.update(new_tokens)
                    access_token = new_tokens["access_token"]
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return None
            else:
                logger.warning("Token expired but no refresh token available")
                return None
        
        return access_token
    
    def _normalize_ticket(self, ticket: Dict[str, Any], org_id: Optional[str] = None) -> Dict[str, Any]:
        """Normalize Zoho ticket to our ticket format"""
        ticket_id = ticket.get("id")
        subject = ticket.get("subject", "No Subject")
        description = ticket.get("description", "")
        status = ticket.get("status", "Open")
        priority = ticket.get("priority", "Medium")
        
        # Map Zoho priority to severity
        priority_map = {
            "Urgent": "critical",
            "High": "high",
            "Medium": "medium",
            "Low": "low"
        }
        severity = priority_map.get(priority, "medium")
        
        # Map Zoho status to our status
        status_map = {
            "Open": "open",
            "In Progress": "in_progress",
            "On Hold": "open",
            "Escalated": "in_progress",
            "Closed": "resolved"
        }
        normalized_status = status_map.get(status, "open")
        
        return {
            "external_id": str(ticket_id),
            "title": subject,
            "description": description,
            "severity": severity,
            "status": normalized_status,
            "source": "zoho",
            "metadata": {
                "zoho_ticket_id": ticket_id,
                "zoho_status": status,
                "zoho_priority": priority,
                "zoho_created_time": ticket.get("createdTime"),
                "zoho_modified_time": ticket.get("modifiedTime"),
                "zoho_assignee": ticket.get("assignee", {}).get("email") if ticket.get("assignee") else None,
                "org_id": org_id
            }
        }
    
    async def close(self):
        """Close HTTP clients"""
        await self.client.aclose()
        await self.oauth_service.close()

