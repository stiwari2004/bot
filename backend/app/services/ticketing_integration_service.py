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
        escalation_reason: str,
        escalation_level: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Escalate ticket in external ticketing tool with proper assignment and priority
        
        Args:
            db: Database session
            ticket: Ticket object
            escalation_reason: Reason for escalation
            escalation_level: Optional escalation level (standard, urgent, critical).
                              If not provided, will be determined automatically.
            execution_context: Optional context with execution logs, retry count, etc.
            
        Returns:
            True if successful, False otherwise
        """
        # Determine escalation level if not provided
        if not escalation_level:
            from app.services.escalation_service import EscalationService
            escalation_service = EscalationService()
            escalation_context = escalation_service.determine_escalation_level(
                db=db,
                ticket=ticket,
                escalation_reason=escalation_reason,
                execution_context=execution_context
            )
            escalation_level = escalation_context.get("escalation_level", "standard")
        else:
            # If level provided, still get context for comment building
            from app.services.escalation_service import EscalationService
            escalation_service = EscalationService()
            escalation_context = escalation_service.determine_escalation_level(
                db=db,
                ticket=ticket,
                escalation_reason=escalation_reason,
                execution_context=execution_context
            )
        
        # Build detailed escalation comment
        execution_logs = execution_context.get("execution_logs") if execution_context else None
        escalation_comment = escalation_service.build_escalation_comment(
            escalation_reason=escalation_reason,
            escalation_context=escalation_context,
            execution_logs=execution_logs
        )
        
        # Update ticket with escalation context
        if ticket.meta_data is None:
            ticket.meta_data = {}
        if isinstance(ticket.meta_data, str):
            ticket.meta_data = json.loads(ticket.meta_data)
        
        ticket.meta_data["escalation_context"] = escalation_context
        ticket.escalation_reason = escalation_reason
        
        # Update ticket status
        return await self._update_ticket_status(
            db=db,
            ticket=ticket,
            status="escalated",
            comment=escalation_comment,
            escalation_context=escalation_context
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
        comment: str,
        escalation_context: Optional[Dict[str, Any]] = None
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
        
        logger.info(f"Attempting to update external ticket {ticket.external_id} (internal ticket {ticket.id}) to status '{status}'")
        logger.info(f"Ticket source: '{ticket.source}'")
        
        # Find ticketing tool connection for this ticket
        # Match by source (ticket.source should match connection.tool_name)
        # Map ticket source to tool_name (e.g., "servicenow" -> "servicenow", "manageengine" -> "manageengine")
        tool_name_map = {
            "servicenow": "servicenow",
            "manageengine": "manageengine",
            "zoho": "zoho"
        }
        
        # Get the tool name from ticket source
        expected_tool_name = tool_name_map.get(ticket.source.lower(), ticket.source.lower())
        
        # First try to match by tool_name matching ticket source
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == ticket.tenant_id,
            TicketingToolConnection.is_active == True,
            TicketingToolConnection.tool_name.ilike(f"%{expected_tool_name}%")
        ).first()
        
        # If no match found, fall back to any active connection (for backward compatibility)
        if not connection:
            logger.warning(f"No active ticketing connection found matching source '{ticket.source}' for tenant {ticket.tenant_id}, trying any active connection...")
            connection = db.query(TicketingToolConnection).filter(
                TicketingToolConnection.tenant_id == ticket.tenant_id,
                TicketingToolConnection.is_active == True
            ).first()
        
        if not connection:
            logger.warning(f"No active ticketing connection found for tenant {ticket.tenant_id}")
            return False
        
        logger.info(f"Found active ticketing connection: {connection.tool_name} for tenant {ticket.tenant_id} (ticket source: {ticket.source})")
        
        # Verify the connection matches the ticket source
        if connection.tool_name.lower() != expected_tool_name:
            logger.warning(
                f"⚠️ Connection tool_name '{connection.tool_name}' doesn't match ticket source '{ticket.source}'. "
                f"This might cause update to fail. Expected: {expected_tool_name}"
            )
        
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
            elif connection.tool_name.lower() == "servicenow":
                return await self._update_servicenow_ticket(
                    connection=connection,
                    external_id=ticket.external_id,
                    status=status,
                    comment=comment,
                    escalation_context=escalation_context
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
                "closed": "Resolved",  # Map "closed" to "Resolved" for ManageEngine
                "resolved": "Resolved",
                "escalated": "In Progress",  # ManageEngine doesn't have "escalated", use In Progress
                "in_progress": "In Progress"
            }
            
            me_status = status_map.get(status, "In Progress")
            logger.info(f"Updating ManageEngine ticket {external_id} to status '{me_status}' (mapped from '{status}')")
            
            # Build API URL
            api_base_url = connection.api_base_url or ""
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            api_url = f"{api_base_url}/api/v3/requests/{external_id}"
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/vnd.manageengine.sdp.v3+json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Build request data - ManageEngine API v3 requires input_data as form-encoded body parameter
            # According to Postman docs: input_data must be sent as form-encoded body, NOT query parameter
            import json
            
            # ManageEngine API v3 doesn't allow updating status and comments in the same request
            request_data = {
                "request": {
                    "status": {
                        "name": me_status
                    }
                }
            }
            
            # ManageEngine API v3 requires input_data as form-encoded body parameter (like POST requests)
            # NOT as query parameter for PUT requests
            form_data = {
                "input_data": json.dumps(request_data)
            }
            
            logger.debug(f"ManageEngine update request: URL={api_url}, form_data={form_data}, headers={dict(headers)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Update status only (ManageEngine API v3 doesn't allow status + comments in same request)
                # Use form-encoded body with input_data parameter (NOT query params, NOT raw JSON)
                response = await client.put(
                    api_url,
                    headers=headers,
                    data=form_data  # Use data= for form-encoded body, NOT params= for query params
                )
                
                if response.status_code in [200, 204]:
                    # ManageEngine returns 200 with JSON body containing response_status
                    # Example: {"response_status": {"status_code": 2000, "status": "success"}}
                    try:
                        response_json = response.json()
                        response_status = response_json.get("response_status", {})
                        status_code = response_status.get("status_code")
                        status_text = response_status.get("status")
                        
                        # Check if the request object in response shows the updated status
                        request_obj = response_json.get("request", {})
                        actual_status = request_obj.get("status", {})
                        actual_status_name = actual_status.get("name") if isinstance(actual_status, dict) else None
                        
                        if status_code == 2000 and status_text == "success":
                            logger.info(
                                f"✅ Successfully updated ManageEngine ticket {external_id} to status '{me_status}'. "
                                f"API confirmed status: '{actual_status_name}' (response_status: {status_code})"
                            )
                            # Verify the status was actually updated
                            if actual_status_name and actual_status_name != me_status:
                                logger.warning(
                                    f"⚠️ Status mismatch: Requested '{me_status}' but API returned '{actual_status_name}'. "
                                    f"This might indicate a status mapping issue or the ticket was already in a different state."
                                )
                        else:
                            logger.warning(
                                f"⚠️ ManageEngine returned 200 but response_status indicates issue: "
                                f"status_code={status_code}, status={status_text}"
                            )
                    except Exception as e:
                        # If JSON parsing fails, still consider it success if HTTP status is 200
                        logger.info(f"✅ Successfully updated ManageEngine ticket {external_id} status to {me_status} (HTTP 200, JSON parse failed: {e})")
                    
                    # Note: Comment will be added in a future update if needed
                    if comment:
                        logger.debug(f"Comment provided but not added (requires separate API call): {comment[:50]}...")
                    return True
                else:
                    error_text = response.text[:500] if hasattr(response, 'text') else str(response.content)[:500]
                    logger.error(f"❌ Failed to update ManageEngine ticket status: {response.status_code} - {error_text}")
                    logger.error(f"Request URL: {api_url}")
                    logger.error(f"Request form_data: {form_data}")
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
    
    async def _update_servicenow_ticket(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        status: str,
        comment: str,
        escalation_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update incident status in ServiceNow
        
        Args:
            connection: Ticketing tool connection
            external_id: External incident number or sys_id
            status: Status to set
            comment: Comment to add
            
        Returns:
            True if successful
        """
        try:
            from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
            import httpx
            import base64
            
            # Get authentication using ServiceNow fetcher
            fetcher = ServiceNowTicketFetcher()
            # Parse meta_data (stored as JSON string)
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            
            # Build API base URL
            api_base_url = connection.api_base_url or connection_meta.get("api_base_url", "")
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            # Get auth headers
            # Credentials can be in meta_data OR in connection.api_username/api_password
            username = connection_meta.get("username") or connection.api_username
            password = connection_meta.get("password") or connection.api_password
            headers = await fetcher._get_auth_headers(
                api_base_url=api_base_url,
                connection_meta=connection_meta,
                username=username,
                password=password,
                client_id=connection_meta.get("client_id"),
                client_secret=connection_meta.get("client_secret")
            )
            
            # Status mapping for ServiceNow
            # ServiceNow uses different values for incident_state vs state fields:
            # - incident_state: 1=New, 2=In Progress, 3=On Hold, 4=Resolved, 5=Closed, 6=Canceled
            # - state: Uses different values (6=Resolved based on Postman testing)
            # IMPORTANT: Use 4 for incident_state and 6 for state when resolving
            state_map = {
                "closed": "5",  # Closed (cannot be reopened - use with caution)
                "resolved": "4",  # Resolved (can be reopened if needed) - for incident_state field
                "escalated": "2",  # In Progress
                "in_progress": "2"  # In Progress
            }
            
            # State value for 'state' field (different from incident_state)
            state_field_map = {
                "closed": "5",
                "resolved": "6",  # state field uses 6 for Resolved (not 4!)
                "escalated": "2",
                "in_progress": "2"
            }
            
            snow_state = state_map.get(status, "2")  # For incident_state field
            snow_state_field = state_field_map.get(status, "2")  # For state field
            logger.info(f"Updating ServiceNow incident {external_id} to incident_state '{snow_state}' and state '{snow_state_field}' (mapped from '{status}')")
            
            # ServiceNow PATCH API requires sys_id (UUID), not the incident number
            # If external_id looks like a number (INC0012345), we need to resolve it to sys_id first
            actual_sys_id = external_id
            
            # Check if external_id is a number (starts with "INC") or sys_id (UUID format)
            # UUIDs are typically 32 hex characters (with or without dashes)
            is_number = external_id.startswith("INC")
            is_uuid = len(external_id) >= 32 and all(c in '0123456789abcdefABCDEF-' for c in external_id.replace('-', ''))
            
            if is_number and not is_uuid:
                # It's a number, need to resolve to sys_id
                logger.info(f"External ID '{external_id}' is an incident number, resolving to sys_id...")
                try:
                    # Query ServiceNow to get sys_id from number
                    query_url = f"{api_base_url}/api/now/table/incident"
                    query_params = {
                        "sysparm_query": f"number={external_id}",
                        "sysparm_fields": "sys_id,number",
                        "sysparm_limit": 1
                    }
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        query_response = await client.get(
                            query_url,
                            headers=headers,
                            params=query_params
                        )
                        
                        if query_response.status_code == 200:
                            query_result = query_response.json()
                            incidents = query_result.get("result", [])
                            if incidents and len(incidents) > 0:
                                actual_sys_id = incidents[0].get("sys_id")
                                if actual_sys_id:
                                    logger.info(f"Resolved incident number '{external_id}' to sys_id '{actual_sys_id}'")
                                else:
                                    logger.error(f"ServiceNow returned incident but no sys_id for number '{external_id}'")
                                    return False
                            else:
                                logger.error(f"Could not find incident with number '{external_id}' in ServiceNow")
                                return False
                        else:
                            error_text = query_response.text[:500] if hasattr(query_response, 'text') else str(query_response.content)[:500]
                            logger.error(f"Failed to query ServiceNow for incident number '{external_id}': {query_response.status_code} - {error_text}")
                            return False
                except Exception as e:
                    logger.error(f"Error resolving incident number '{external_id}' to sys_id: {e}", exc_info=True)
                    return False
            else:
                logger.info(f"Using external_id '{external_id}' as sys_id (assuming it's already a sys_id)")
            
            # Use sys_id for the update
            api_url = f"{api_base_url}/api/now/table/incident/{actual_sys_id}"
            logger.info(f"Updating ServiceNow incident using sys_id: {actual_sys_id}")
            
            # Build request data
            # Based on Stack Overflow: https://stackoverflow.com/questions/52937955/cant-resolve-servicenow-incident-using-rest-api
            # ServiceNow may require:
            # 1. automated_state_flow=false to bypass business rules
            # 2. incident_state field (not state) for some instances
            # 3. All mandatory fields must be set
            from datetime import datetime, timezone
            
            # ServiceNow requires additional fields when resolving/closing incidents
            # For state 4 (Resolved) or 5 (Closed), we need close_code, close_notes, active=false, and resolved_at
            if snow_state in ["4", "5"]:  # Resolved or Closed
                # Try two-step approach: First disable automated state flow, then set state
                # Step 1: Set automated_state_flow to False (bypasses business rules)
                logger.info(f"Step 1: Setting automated_state_flow=False for incident {external_id}")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    step1_response = await client.patch(
                        api_url,
                        headers=headers,
                        json={"automated_state_flow": False}
                    )
                    if step1_response.status_code not in [200, 204]:
                        logger.warning(f"Failed to set automated_state_flow=False: {step1_response.status_code} - {step1_response.text[:200]}")
                
                # Step 2: Set all resolution fields including state
                # Based on Postman testing: incident_state="4" and state="6" both need to be set
                request_data = {
                    "incident_state": snow_state,  # "4" for Resolved
                    "state": snow_state_field,  # "6" for Resolved (different from incident_state!)
                    "automated_state_flow": False,  # Keep this set
                    "active": False,  # Set active to false
                    "resolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "close_code": "Solution provided",  # Enumeration field - must match instance values
                }
                
                # Set close_notes from comment if provided
                if comment:
                    request_data["close_notes"] = comment
                    # Also add as work notes for visibility
                    request_data["work_notes"] = comment
                else:
                    # Default close notes if no comment provided
                    request_data["close_notes"] = "Resolved by AI Agent"
            else:
                # For other states (In Progress, etc.), add work notes and escalation fields
                request_data = {
                    "state": snow_state,
                    "incident_state": snow_state
                }
                if comment:
                    request_data["work_notes"] = comment
                
                # Add escalation fields if escalation context provided
                if escalation_context and status == "escalated":
                    # Set assignment group (requires sys_id of the group)
                    assignment_group = escalation_context.get("assignment_group")
                    if assignment_group:
                        # Try to resolve assignment group name to sys_id
                        # If assignment_group is already a sys_id (UUID), use it directly
                        # Otherwise, query ServiceNow to get sys_id from name
                        group_sys_id = await self._resolve_servicenow_group_sys_id(
                            api_base_url=api_base_url,
                            headers=headers,
                            group_name=assignment_group
                        )
                        if group_sys_id:
                            request_data["assignment_group"] = group_sys_id
                            logger.info(f"Setting assignment_group to '{group_sys_id}' (resolved from '{assignment_group}')")
                        else:
                            # Fallback: try using name directly (some ServiceNow instances allow this)
                            request_data["assignment_group"] = assignment_group
                            logger.warning(f"Could not resolve assignment group '{assignment_group}' to sys_id, using name directly")
                    
                    # Set priority (1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning)
                    priority = escalation_context.get("priority")
                    if priority:
                        request_data["priority"] = priority
                        logger.info(f"Setting priority to '{priority}'")
                    
                    # Set urgency (1=Critical, 2=High, 3=Medium, 4=Low)
                    urgency = escalation_context.get("urgency")
                    if urgency:
                        request_data["urgency"] = urgency
                        logger.info(f"Setting urgency to '{urgency}'")
                    
                    # Set impact (1=High, 2=Medium, 3=Low)
                    impact = escalation_context.get("impact")
                    if impact:
                        request_data["impact"] = impact
                        logger.info(f"Setting impact to '{impact}'")
            
            # Log the request data for debugging
            logger.info(f"ServiceNow update request data: {request_data}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    api_url,
                    headers=headers,
                    json=request_data
                )
                
                if response.status_code in [200, 204]:
                    try:
                        result = response.json()
                        updated_incident = result.get("result", {})
                        # Check both 'incident_state' and 'state' fields (ServiceNow may return either)
                        actual_state = updated_incident.get("incident_state") or updated_incident.get("state")
                        actual_number = updated_incident.get("number")
                        actual_close_code = updated_incident.get("close_code")
                        actual_active = updated_incident.get("active")
                        
                        logger.info(
                            f"✅ ServiceNow API returned HTTP {response.status_code} for incident {external_id}. "
                            f"Requested state: '{snow_state}', API returned incident_state: '{actual_state}', "
                            f"number: '{actual_number}', active: '{actual_active}', close_code: '{actual_close_code}'"
                        )
                        
                        # Verify the state was actually updated
                        # ServiceNow may return different state values (e.g., '6' for resolved when we request '4')
                        # Check if the ticket is actually resolved/closed (state 4, 5, or 6) rather than exact match
                        actual_state_str = str(actual_state) if actual_state else ""
                        requested_state_str = str(snow_state)
                        
                        # For resolved/closed states, accept 4, 5, or 6 as success
                        if snow_state in ["4", "5"]:  # Resolved or Closed
                            if actual_state_str in ["4", "5", "6"]:
                                # Success - ticket is resolved/closed
                                logger.info(
                                    f"✅ Successfully updated ServiceNow incident {external_id} to resolved/closed state. "
                                    f"Requested: '{snow_state}', API returned: '{actual_state_str}', "
                                    f"Close code: '{actual_close_code}', Active: '{actual_active}'"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ State mismatch: Requested resolved/closed ('{snow_state}') but API returned '{actual_state_str}'. "
                                    f"This might indicate:"
                                    f"  1. Missing required fields (close_code, close_notes, active=false) for resolved/closed state"
                                    f"  2. ACL/permissions issue preventing state change"
                                    f"  3. Business rule preventing the transition"
                                    f"  4. State transition workflow requirements not met"
                                )
                                return False
                        else:
                            # For other states, check exact match
                            if actual_state_str != requested_state_str:
                                logger.warning(
                                    f"⚠️ State mismatch: Requested '{snow_state}' but API returned '{actual_state_str}'"
                                )
                                return False
                            else:
                                logger.info(
                                    f"✅ Successfully updated ServiceNow incident {external_id} to state '{snow_state}'. "
                                    f"Close code: '{actual_close_code}', Active: '{actual_active}'"
                                )
                    except Exception as e:
                        # If JSON parsing fails, still consider it success if HTTP status is 200
                        logger.info(f"✅ Successfully updated ServiceNow incident {external_id} state to {snow_state} (HTTP 200, JSON parse failed: {e})")
                    
                    return True
                else:
                    error_text = response.text[:500] if hasattr(response, 'text') else str(response.content)[:500]
                    logger.error(f"❌ Failed to update ServiceNow incident status: {response.status_code} - {error_text}")
                    logger.error(f"Request URL: {api_url}")
                    logger.error(f"Request data: {request_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating ServiceNow incident: {e}", exc_info=True)
            return False
    
    async def _resolve_servicenow_group_sys_id(
        self,
        api_base_url: str,
        headers: Dict[str, str],
        group_name: str
    ) -> Optional[str]:
        """
        Resolve ServiceNow group name to sys_id
        
        Args:
            api_base_url: ServiceNow API base URL
            headers: Authentication headers
            group_name: Group name or sys_id
            
        Returns:
            Group sys_id if found, None otherwise
        """
        # If group_name is already a UUID (sys_id), return it
        if len(group_name) >= 32 and all(c in '0123456789abcdefABCDEF-' for c in group_name.replace('-', '')):
            logger.info(f"Group name '{group_name}' appears to be a sys_id, using directly")
            return group_name
        
        try:
            import httpx
            
            # Query ServiceNow sys_user_group table
            query_url = f"{api_base_url}/api/now/table/sys_user_group"
            query_params = {
                "sysparm_query": f"name={group_name}",
                "sysparm_fields": "sys_id,name",
                "sysparm_limit": 1
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    query_url,
                    headers=headers,
                    params=query_params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    groups = result.get("result", [])
                    if groups and len(groups) > 0:
                        group_sys_id = groups[0].get("sys_id")
                        logger.info(f"Resolved group name '{group_name}' to sys_id '{group_sys_id}'")
                        return group_sys_id
                    else:
                        logger.warning(f"Could not find group '{group_name}' in ServiceNow")
                        return None
                else:
                    logger.warning(f"Failed to query ServiceNow for group '{group_name}': {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error resolving ServiceNow group '{group_name}' to sys_id: {e}", exc_info=True)
            return None
    
    async def add_ticket_comment(
        self,
        db: Session,
        ticket: Ticket,
        comment: str
    ) -> bool:
        """
        Add a comment to external ticketing system without changing status
        
        Args:
            db: Database session
            ticket: Ticket object
            comment: Comment text to add
            
        Returns:
            True if successful, False otherwise
        """
        if not ticket.external_id:
            logger.debug(f"Ticket {ticket.id} has no external_id, skipping comment")
            return False
        
        logger.info(f"Adding comment to external ticket {ticket.external_id} (internal ticket {ticket.id})")
        
        # Find ticketing tool connection
        tool_name_map = {
            "servicenow": "servicenow",
            "manageengine": "manageengine",
            "zoho": "zoho"
        }
        
        expected_tool_name = tool_name_map.get(ticket.source.lower(), ticket.source.lower())
        
        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == ticket.tenant_id,
            TicketingToolConnection.is_active == True,
            TicketingToolConnection.tool_name.ilike(f"%{expected_tool_name}%")
        ).first()
        
        if not connection:
            logger.warning(f"No active ticketing connection found for tenant {ticket.tenant_id}")
            return False
        
        try:
            # Add comment based on tool type
            if connection.tool_name.lower() == "manageengine":
                return await self._add_manageengine_comment(
                    connection=connection,
                    external_id=ticket.external_id,
                    comment=comment
                )
            elif connection.tool_name.lower() == "zoho":
                return await self._add_zoho_comment(
                    connection=connection,
                    external_id=ticket.external_id,
                    comment=comment
                )
            elif connection.tool_name.lower() == "servicenow":
                return await self._add_servicenow_comment(
                    connection=connection,
                    external_id=ticket.external_id,
                    comment=comment
                )
            else:
                logger.warning(f"Ticketing tool {connection.tool_name} not supported for comments")
                return False
                
        except Exception as e:
            logger.error(f"Error adding comment to ticket {ticket.id} in external system: {e}", exc_info=True)
            return False
        finally:
            # Update external_ticket_updated_at timestamp
            ticket.external_ticket_updated_at = datetime.now(timezone.utc)
            db.commit()
    
    async def _add_manageengine_comment(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        comment: str
    ) -> bool:
        """Add comment to ManageEngine ticket"""
        try:
            from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
            import httpx
            import json
            
            fetcher = ManageEngineTicketFetcher()
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            
            access_token = await fetcher._get_valid_token(connection_meta)
            api_domain = connection.api_base_url or connection_meta.get("api_domain", "")
            if not api_domain.startswith("http"):
                api_domain = f"https://{api_domain}"
            
            # ManageEngine API v3 - Add comment
            comment_url = f"{api_domain}/api/v3/tickets/{external_id}/comments"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            comment_data = {
                "content": comment,
                "isPublic": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(comment_url, headers=headers, json=comment_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Successfully added comment to ManageEngine ticket {external_id}")
                    return True
                else:
                    logger.error(f"Failed to add comment to ManageEngine ticket: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding ManageEngine comment: {e}", exc_info=True)
            return False
    
    async def _add_zoho_comment(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        comment: str
    ) -> bool:
        """Add comment to Zoho ticket"""
        try:
            from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
            import httpx
            import json
            
            fetcher = ZohoTicketFetcher()
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            
            access_token = await fetcher._get_valid_token(connection_meta)
            api_domain = connection.api_base_url or connection_meta.get("api_domain") or "https://desk.zoho.com"
            if not api_domain.startswith("http"):
                api_domain = f"https://{api_domain}"
            
            org_id = connection_meta.get("org_id")
            if not org_id:
                logger.error("Zoho org_id not found in connection metadata")
                return False
            
            comment_url = f"{api_domain}/api/v1/tickets/{external_id}/comments"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json",
                "orgId": org_id
            }
            
            comment_data = {
                "content": comment,
                "isPublic": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(comment_url, headers=headers, json=comment_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Successfully added comment to Zoho ticket {external_id}")
                    return True
                else:
                    logger.error(f"Failed to add comment to Zoho ticket: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding Zoho comment: {e}", exc_info=True)
            return False
    
    async def _add_servicenow_comment(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        comment: str
    ) -> bool:
        """Add comment to ServiceNow incident"""
        try:
            from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
            import httpx
            import base64
            
            fetcher = ServiceNowTicketFetcher()
            if isinstance(connection.meta_data, str):
                connection_meta = json.loads(connection.meta_data) if connection.meta_data else {}
            else:
                connection_meta = connection.meta_data if isinstance(connection.meta_data, dict) else {}
            
            api_base_url = connection.api_base_url or connection_meta.get("api_base_url", "")
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            
            # ServiceNow uses basic auth or OAuth
            username = connection_meta.get("username") or connection_meta.get("user")
            password = connection_meta.get("password")
            
            if username and password:
                # Basic auth
                auth_string = f"{username}:{password}"
                auth_bytes = auth_string.encode("utf-8")
                auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
                headers = {
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            else:
                logger.error("ServiceNow authentication credentials not found")
                return False
            
            # ServiceNow uses sys_id for updates, but we might have incident number
            # Try to get sys_id if we have incident number
            if not external_id.startswith("sys_"):
                # Query for sys_id using incident number
                query_url = f"{api_base_url}/api/now/table/incident?sysparm_query=number={external_id}&sysparm_fields=sys_id"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    query_response = await client.get(query_url, headers=headers)
                    if query_response.status_code == 200:
                        result = query_response.json()
                        if result.get("result") and len(result["result"]) > 0:
                            external_id = result["result"][0]["sys_id"]
                        else:
                            logger.warning(f"ServiceNow incident {external_id} not found")
                            return False
                    else:
                        logger.error(f"Failed to query ServiceNow incident: {query_response.status_code}")
                        return False
            
            # Add comment using journal entry
            comment_url = f"{api_base_url}/api/now/table/incident/{external_id}"
            request_data = {
                "comments": comment
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(comment_url, headers=headers, json=request_data)
                
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully added comment to ServiceNow incident {external_id}")
                    return True
                else:
                    logger.error(f"Failed to add comment to ServiceNow incident: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding ServiceNow comment: {e}", exc_info=True)
            return False


# Global instance
_ticketing_integration_service: Optional[TicketingIntegrationService] = None


def get_ticketing_integration_service() -> TicketingIntegrationService:
    """Get or create ticketing integration service instance"""
    global _ticketing_integration_service
    if _ticketing_integration_service is None:
        _ticketing_integration_service = TicketingIntegrationService()
    return _ticketing_integration_service

