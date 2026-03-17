"""
Ticket Status Updater — tool-specific status update implementations
"""
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.ticketing_tool_connection import TicketingToolConnection

logger = get_logger(__name__)


class TicketStatusUpdater:
    """Handles updating ticket status in external ticketing systems"""

    async def update_ticket_status(
        self,
        db: Session,
        ticket: Ticket,
        status: str,
        comment: str,
        escalation_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not ticket.external_id:
            logger.warning(f"Ticket {ticket.id} has no external_id, skipping external update")
            return False

        logger.info(
            f"Attempting to update external ticket {ticket.external_id} "
            f"(internal ticket {ticket.id}) to status '{status}'"
        )
        logger.info(f"Ticket source: '{ticket.source}'")

        tool_name_map = {"servicenow": "servicenow", "manageengine": "manageengine", "zoho": "zoho"}
        expected_tool_name = tool_name_map.get(ticket.source.lower(), ticket.source.lower())

        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == ticket.tenant_id,
            TicketingToolConnection.is_active == True,
            TicketingToolConnection.tool_name.ilike(f"%{expected_tool_name}%"),
        ).first()

        if not connection:
            logger.warning(
                f"No active ticketing connection found matching source '{ticket.source}' "
                f"for tenant {ticket.tenant_id}, trying any active connection..."
            )
            connection = db.query(TicketingToolConnection).filter(
                TicketingToolConnection.tenant_id == ticket.tenant_id,
                TicketingToolConnection.is_active == True,
            ).first()

        if not connection:
            logger.warning(f"No active ticketing connection found for tenant {ticket.tenant_id}")
            return False

        logger.info(
            f"Found active ticketing connection: {connection.tool_name} "
            f"for tenant {ticket.tenant_id} (ticket source: {ticket.source})"
        )

        if connection.tool_name.lower() != expected_tool_name:
            logger.warning(
                f"Connection tool_name '{connection.tool_name}' doesn't match ticket source "
                f"'{ticket.source}'. Expected: {expected_tool_name}"
            )

        try:
            if connection.tool_name.lower() == "manageengine":
                return await self._update_manageengine_ticket(
                    connection=connection, external_id=ticket.external_id,
                    status=status, comment=comment,
                )
            elif connection.tool_name.lower() == "zoho":
                return await self._update_zoho_ticket(
                    connection=connection, external_id=ticket.external_id,
                    status=status, comment=comment,
                )
            elif connection.tool_name.lower() == "servicenow":
                return await self._update_servicenow_ticket(
                    connection=connection, external_id=ticket.external_id,
                    status=status, comment=comment, escalation_context=escalation_context,
                )
            else:
                logger.warning(f"Ticketing tool {connection.tool_name} not supported for status updates")
                return False
        except Exception as e:
            logger.error(f"Error updating ticket {ticket.id} in external system: {e}", exc_info=True)
            return False
        finally:
            ticket.external_ticket_updated_at = datetime.now(timezone.utc)
            db.commit()

    async def _update_manageengine_ticket(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        status: str,
        comment: str,
    ) -> bool:
        try:
            from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
            import httpx

            fetcher = ManageEngineTicketFetcher()
            connection_meta = (
                json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else
                (connection.meta_data if isinstance(connection.meta_data, dict) else {})
            )
            access_token = await fetcher._get_valid_token(connection_meta)

            if not access_token:
                logger.error("Failed to get ManageEngine access token")
                return False

            status_map = {
                "closed": "Resolved",
                "resolved": "Resolved",
                "escalated": "In Progress",
                "in_progress": "In Progress",
            }
            me_status = status_map.get(status, "In Progress")
            logger.info(f"Updating ManageEngine ticket {external_id} to status '{me_status}' (mapped from '{status}')")

            api_base_url = connection.api_base_url or ""
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")
            api_url = f"{api_base_url}/api/v3/requests/{external_id}"

            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/vnd.manageengine.sdp.v3+json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            request_data = {"request": {"status": {"name": me_status}}}
            form_data = {"input_data": json.dumps(request_data)}

            logger.debug(f"ManageEngine update request: URL={api_url}, form_data={form_data}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(api_url, headers=headers, data=form_data)

                if response.status_code in [200, 204]:
                    try:
                        response_json = response.json()
                        response_status = response_json.get("response_status", {})
                        status_code = response_status.get("status_code")
                        status_text = response_status.get("status")
                        request_obj = response_json.get("request", {})
                        actual_status_name = (
                            request_obj.get("status", {}).get("name")
                            if isinstance(request_obj.get("status"), dict) else None
                        )

                        if status_code == 2000 and status_text == "success":
                            logger.info(
                                f"Successfully updated ManageEngine ticket {external_id} to '{me_status}'. "
                                f"API confirmed status: '{actual_status_name}'"
                            )
                            if actual_status_name and actual_status_name != me_status:
                                logger.warning(
                                    f"Status mismatch: Requested '{me_status}' but API returned '{actual_status_name}'"
                                )
                        else:
                            logger.warning(
                                f"ManageEngine returned 200 but response_status indicates issue: "
                                f"status_code={status_code}, status={status_text}"
                            )
                    except Exception as e:
                        logger.info(
                            f"Successfully updated ManageEngine ticket {external_id} status to {me_status} "
                            f"(HTTP 200, JSON parse failed: {e})"
                        )

                    if comment:
                        logger.debug(f"Comment provided but not added (requires separate API call): {comment[:50]}...")
                    return True
                else:
                    error_text = response.text[:500] if hasattr(response, "text") else str(response.content)[:500]
                    logger.error(f"Failed to update ManageEngine ticket status: {response.status_code} - {error_text}")
                    logger.error(f"Request URL: {api_url}, form_data: {form_data}")
                    return False

        except Exception as e:
            logger.error(f"Error updating ManageEngine ticket: {e}", exc_info=True)
            return False

    async def _update_zoho_ticket(
        self,
        connection: TicketingToolConnection,
        external_id: str,
        status: str,
        comment: str,
    ) -> bool:
        try:
            from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
            import httpx

            fetcher = ZohoTicketFetcher()
            connection_meta = (
                json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else
                (connection.meta_data if isinstance(connection.meta_data, dict) else {})
            )
            access_token = await fetcher._get_valid_token(connection_meta)

            if not access_token:
                logger.error("Failed to get Zoho access token")
                return False

            status_map = {
                "closed": "Closed", "resolved": "Resolved",
                "escalated": "In Progress", "in_progress": "In Progress",
            }
            zoho_status = status_map.get(status, "In Progress")

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
                "orgId": org_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(api_url, headers=headers, json={"status": zoho_status})

                if response.status_code in [200, 204]:
                    logger.info(f"Successfully updated Zoho ticket {external_id} to {zoho_status}")
                    if comment:
                        comment_url = f"{api_domain}/api/v1/tickets/{external_id}/comments"
                        comment_response = await client.post(
                            comment_url, headers=headers, json={"content": comment, "isPublic": True}
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
        escalation_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
            import httpx

            fetcher = ServiceNowTicketFetcher()
            connection_meta = (
                json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else
                (connection.meta_data if isinstance(connection.meta_data, dict) else {})
            )

            api_base_url = connection.api_base_url or connection_meta.get("api_base_url", "")
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")

            username = connection_meta.get("username") or connection.api_username
            password = connection_meta.get("password") or connection.api_password
            headers = await fetcher._get_auth_headers(
                api_base_url=api_base_url,
                connection_meta=connection_meta,
                username=username,
                password=password,
                client_id=connection_meta.get("client_id"),
                client_secret=connection_meta.get("client_secret"),
            )

            state_map = {"closed": "5", "resolved": "4", "escalated": "2", "in_progress": "2"}
            state_field_map = {"closed": "5", "resolved": "6", "escalated": "2", "in_progress": "2"}
            snow_state = state_map.get(status, "2")
            snow_state_field = state_field_map.get(status, "2")
            logger.info(
                f"Updating ServiceNow incident {external_id} to incident_state '{snow_state}' "
                f"and state '{snow_state_field}' (mapped from '{status}')"
            )

            # Resolve incident number to sys_id if needed
            actual_sys_id = external_id
            is_number = external_id.startswith("INC")
            is_uuid = len(external_id) >= 32 and all(c in "0123456789abcdefABCDEF-" for c in external_id.replace("-", ""))

            if is_number and not is_uuid:
                logger.info(f"External ID '{external_id}' is an incident number, resolving to sys_id...")
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        query_response = await client.get(
                            f"{api_base_url}/api/now/table/incident",
                            headers=headers,
                            params={"sysparm_query": f"number={external_id}", "sysparm_fields": "sys_id,number", "sysparm_limit": 1},
                        )
                        if query_response.status_code == 200:
                            incidents = query_response.json().get("result", [])
                            if incidents:
                                actual_sys_id = incidents[0].get("sys_id")
                                if not actual_sys_id:
                                    logger.error(f"ServiceNow returned incident but no sys_id for number '{external_id}'")
                                    return False
                                logger.info(f"Resolved incident number '{external_id}' to sys_id '{actual_sys_id}'")
                            else:
                                logger.error(f"Could not find incident with number '{external_id}' in ServiceNow")
                                return False
                        else:
                            logger.error(
                                f"Failed to query ServiceNow for incident number '{external_id}': "
                                f"{query_response.status_code}"
                            )
                            return False
                except Exception as e:
                    logger.error(f"Error resolving incident number '{external_id}' to sys_id: {e}", exc_info=True)
                    return False
            else:
                logger.info(f"Using external_id '{external_id}' as sys_id")

            api_url = f"{api_base_url}/api/now/table/incident/{actual_sys_id}"

            if snow_state in ["4", "5"]:
                # Disable automated state flow first
                async with httpx.AsyncClient(timeout=30.0) as client:
                    step1_response = await client.patch(api_url, headers=headers, json={"automated_state_flow": False})
                    if step1_response.status_code not in [200, 204]:
                        logger.warning(
                            f"Failed to set automated_state_flow=False: "
                            f"{step1_response.status_code} - {step1_response.text[:200]}"
                        )

                request_data: Dict[str, Any] = {
                    "incident_state": snow_state,
                    "state": snow_state_field,
                    "automated_state_flow": False,
                    "active": False,
                    "resolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "close_code": "Solution provided",
                    "close_notes": comment if comment else "Resolved by AI Agent",
                }
                if comment:
                    request_data["work_notes"] = comment
            else:
                request_data = {"state": snow_state, "incident_state": snow_state}
                if comment:
                    request_data["work_notes"] = comment

                if escalation_context and status == "escalated":
                    assignment_group = escalation_context.get("assignment_group")
                    if assignment_group:
                        group_sys_id = await self._resolve_servicenow_group_sys_id(
                            api_base_url=api_base_url, headers=headers, group_name=assignment_group
                        )
                        request_data["assignment_group"] = group_sys_id or assignment_group

                    for field in ("priority", "urgency", "impact"):
                        if escalation_context.get(field):
                            request_data[field] = escalation_context[field]

            logger.info(f"ServiceNow update request data: {request_data}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(api_url, headers=headers, json=request_data)

                if response.status_code in [200, 204]:
                    try:
                        updated_incident = response.json().get("result", {})
                        actual_state = updated_incident.get("incident_state") or updated_incident.get("state")
                        actual_state_str = str(actual_state) if actual_state else ""

                        if snow_state in ["4", "5"]:
                            if actual_state_str in ["4", "5", "6"]:
                                logger.info(
                                    f"Successfully updated ServiceNow incident {external_id} to resolved/closed. "
                                    f"Requested: '{snow_state}', API returned: '{actual_state_str}'"
                                )
                            else:
                                logger.warning(
                                    f"State mismatch: Requested resolved/closed ('{snow_state}') "
                                    f"but API returned '{actual_state_str}'"
                                )
                                return False
                        else:
                            if actual_state_str != str(snow_state):
                                logger.warning(
                                    f"State mismatch: Requested '{snow_state}' but API returned '{actual_state_str}'"
                                )
                                return False
                            else:
                                logger.info(f"Successfully updated ServiceNow incident {external_id} to state '{snow_state}'")
                    except Exception as e:
                        logger.info(
                            f"Successfully updated ServiceNow incident {external_id} state to {snow_state} "
                            f"(HTTP 200, JSON parse failed: {e})"
                        )
                    return True
                else:
                    error_text = response.text[:500] if hasattr(response, "text") else str(response.content)[:500]
                    logger.error(f"Failed to update ServiceNow incident status: {response.status_code} - {error_text}")
                    logger.error(f"Request URL: {api_url}, data: {request_data}")
                    return False

        except Exception as e:
            logger.error(f"Error updating ServiceNow incident: {e}", exc_info=True)
            return False

    async def _resolve_servicenow_group_sys_id(
        self,
        api_base_url: str,
        headers: Dict[str, str],
        group_name: str,
    ) -> Optional[str]:
        if len(group_name) >= 32 and all(c in "0123456789abcdefABCDEF-" for c in group_name.replace("-", "")):
            logger.info(f"Group name '{group_name}' appears to be a sys_id, using directly")
            return group_name

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base_url}/api/now/table/sys_user_group",
                    headers=headers,
                    params={"sysparm_query": f"name={group_name}", "sysparm_fields": "sys_id,name", "sysparm_limit": 1},
                )
                if response.status_code == 200:
                    groups = response.json().get("result", [])
                    if groups:
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
