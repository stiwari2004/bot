"""
Ticketing Integration Service - Update tickets in external ticketing tools
"""
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.ticketing_tool_connection import TicketingToolConnection

logger = get_logger(__name__)


class TicketingIntegrationService:
    """Service for updating tickets in external ticketing tools"""
    
    async def close_ticket(
        self,
        db: Session,
        ticket: Ticket,
        reason: str
    ) -> bool:
        """
        Close ticket in external ticketing tool
        
        Args:
            db: Database session
            ticket: Ticket object
            reason: Reason for closing
            
        Returns:
            True if successful, False otherwise
        """
        return await self._update_ticket_status(
            db=db,
            ticket=ticket,
            status="closed",
            comment=reason
        )
    
    async def resolve_ticket(
        self,
        db: Session,
        ticket: Ticket,
        resolution_notes: str
    ) -> bool:
        """
        Resolve ticket in external ticketing tool
        
        Args:
            db: Database session
            ticket: Ticket object
            resolution_notes: Resolution notes/description
            
        Returns:
            True if successful, False otherwise
        """
        return await self._update_ticket_status(
            db=db,
            ticket=ticket,
            status="resolved",
            comment=resolution_notes
        )
    
    async def escalate_ticket(
        self,
        db: Session,
        ticket: Ticket,
        escalation_reason: str
    ) -> bool:
        """
        Escalate ticket in external ticketing tool
        
        Args:
            db: Database session
            ticket: Ticket object
            escalation_reason: Reason for escalation
            
        Returns:
            True if successful, False otherwise
        """
        return await self._update_ticket_status(
            db=db,
            ticket=ticket,
            status="escalated",
            comment=escalation_reason
        )
    
    async def mark_for_manual_review(
        self,
        db: Session,
        ticket: Ticket,
        reason: str
    ) -> bool:
        """
        Mark ticket for manual review in external ticketing tool
        
        Args:
            db: Database session
            ticket: Ticket object
            reason: Reason for manual review
            
        Returns:
            True if successful, False otherwise
        """
        # Most ticketing tools don't have a "manual review" status
        # We'll use "in_progress" or "open" status with a comment
        return await self._update_ticket_status(
            db=db,
            ticket=ticket,
            status="in_progress",
            comment=f"Requires manual review: {reason}"
        )
    
    async def _update_ticket_status(
        self,
        db: Session,
        ticket: Ticket,
        status: str,
        comment: str
    ) -> bool:
        """
        Update ticket status in external ticketing tool
        
        Args:
            db: Database session
            ticket: Ticket object
            status: Status to set
            comment: Comment/notes to add
            
        Returns:
            True if successful, False otherwise
        """
        if not ticket.external_id:
            logger.warning(f"Ticket {ticket.id} has no external_id, skipping external update")
            return False
        
        # Find ticketing tool connection for this ticket
        # We'll match by source or find active connections
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == ticket.tenant_id,
            TicketingToolConnection.is_active == True
        ).first()
        
        if not connection:
            logger.warning(f"No active ticketing connection found for tenant {ticket.tenant_id}")
            return False
        
        try:
            # Update based on tool type
            if connection.tool_name.lower() == "manageengine":
                return await self._update_manageengine_ticket(
                    connection=connection,
                    external_id=ticket.external_id,
                    status=status,
                    comment=comment
                )
            elif connection.tool_name.lower() == "zoho":
                return await self._update_zoho_ticket(
                    connection=connection,
                    external_id=ticket.external_id,
                    status=status,
                    comment=comment
                )
            else:
                logger.warning(f"Ticketing tool {connection.tool_name} not supported for status updates")
                return False
                
        except Exception as e:
            logger.error(f"Error updating ticket {ticket.id} in external system: {e}", exc_info=True)
            return False
        finally:
            # Update external_ticket_updated_at timestamp
            ticket.external_ticket_updated_at = datetime.now(timezone.utc)
            db.commit()
    
    async def _update_manageengine_ticket(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        status: str,
        comment: str
    ) -> bool:
        """
        Update ticket status in ManageEngine
        
        Args:
            connection: Ticketing tool connection
            external_id: External ticket ID
            status: Status to set
            comment: Comment to add
            
        Returns:
            True if successful
        """
        try:
            from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
            import httpx
            import json
            
            # Get OAuth token using ManageEngine fetcher
            fetcher = ManageEngineTicketFetcher()
            # Parse meta_data (stored as JSON string)
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            access_token = await fetcher._get_valid_token(connection_meta)
            
            if not access_token:
                logger.error("Failed to get ManageEngine access token")
                return False
            
            # Status mapping for ManageEngine
            status_map = {
                "closed": "Closed",
                "resolved": "Resolved",
                "escalated": "In Progress",  # ManageEngine doesn't have "escalated", use In Progress
                "in_progress": "In Progress"
            }
            
            me_status = status_map.get(status, "In Progress")
            
            # Build API URL
            api_base_url = connection.api_base_url or ""
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            api_url = f"{api_base_url}/api/v3/requests/{external_id}"
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/vnd.manageengine.sdp.v3+json",
                "Content-Type": "application/json"
            }
            
            # Build request body
            request_data = {
                "request": {
                    "status": {
                        "name": me_status
                    }
                }
            }
            
            # Add comment if provided
            if comment:
                request_data["request"]["comments"] = [{
                    "content": comment,
                    "is_public": True
                }]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    api_url,
                    headers=headers,
                    json=request_data
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully updated ManageEngine ticket {external_id} to {me_status}")
                    return True
                else:
                    logger.error(f"Failed to update ManageEngine ticket: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating ManageEngine ticket: {e}", exc_info=True)
            return False
    
    async def _update_zoho_ticket(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        status: str,
        comment: str
    ) -> bool:
        """
        Update ticket status in Zoho Desk
        
        Args:
            connection: Ticketing tool connection
            external_id: External ticket ID
            status: Status to set
            comment: Comment to add
            
        Returns:
            True if successful
        """
        try:
            from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
            import httpx
            import json
            
            # Get OAuth token using Zoho fetcher
            fetcher = ZohoTicketFetcher()
            # Parse meta_data (stored as JSON string)
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            access_token = await fetcher._get_valid_token(connection_meta)
            
            if not access_token:
                logger.error("Failed to get Zoho access token")
                return False
            
            # Status mapping for Zoho
            status_map = {
                "closed": "Closed",
                "resolved": "Resolved",
                "escalated": "In Progress",
                "in_progress": "In Progress"
            }
            
            zoho_status = status_map.get(status, "In Progress")
            
            # Build API URL
            api_domain = connection.api_base_url or connection_meta.get("api_domain") or "https://desk.zoho.com"
            if not api_domain.startswith("http"):
                api_domain = f"https://{api_domain}"
            
            org_id = connection_meta.get("org_id")
            if not org_id:
                logger.error("Zoho org_id not found in connection metadata")
                return False
            
            api_url = f"{api_domain}/api/v1/tickets/{external_id}"
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json",
                "orgId": org_id
            }
            
            # Build request body
            request_data = {
                "status": zoho_status
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    api_url,
                    headers=headers,
                    json=request_data
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully updated Zoho ticket {external_id} to {zoho_status}")
                    
                    # Add comment if provided
                    if comment:
                        comment_url = f"{api_domain}/api/v1/tickets/{external_id}/comments"
                        comment_data = {
                            "content": comment,
                            "isPublic": True
                        }
                        comment_response = await client.post(
                            comment_url,
                            headers=headers,
                            json=comment_data
                        )
                        if comment_response.status_code not in [200, 201]:
                            logger.warning(f"Failed to add comment to Zoho ticket: {comment_response.status_code}")
                    
                    return True
                else:
                    logger.error(f"Failed to update Zoho ticket: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating Zoho ticket: {e}", exc_info=True)
            return False


# Global instance
_ticketing_integration_service: Optional[TicketingIntegrationService] = None


def get_ticketing_integration_service() -> TicketingIntegrationService:
    """Get or create ticketing integration service instance"""
    global _ticketing_integration_service
    if _ticketing_integration_service is None:
        _ticketing_integration_service = TicketingIntegrationService()
    return _ticketing_integration_service

