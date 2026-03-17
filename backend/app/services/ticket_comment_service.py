"""
Ticket Comment Service — add comments to external ticketing systems
"""
import json
import base64
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.ticketing_tool_connection import TicketingToolConnection

logger = get_logger(__name__)


class TicketCommentService:
    """Handles adding comments to tickets in external ticketing systems"""

    async def add_ticket_comment(
        self,
        db: Session,
        ticket: Ticket,
        comment: str,
    ) -> bool:
        if not ticket.external_id:
            logger.debug(f"Ticket {ticket.id} has no external_id, skipping comment")
            return False

        logger.info(f"Adding comment to external ticket {ticket.external_id} (internal ticket {ticket.id})")

        tool_name_map = {"servicenow": "servicenow", "manageengine": "manageengine", "zoho": "zoho"}
        expected_tool_name = tool_name_map.get(ticket.source.lower(), ticket.source.lower())

        connection = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == ticket.tenant_id,
            TicketingToolConnection.is_active == True,
            TicketingToolConnection.tool_name.ilike(f"%{expected_tool_name}%"),
        ).first()

        if not connection:
            logger.warning(f"No active ticketing connection found for tenant {ticket.tenant_id}")
            return False

        try:
            if connection.tool_name.lower() == "manageengine":
                return await self._add_manageengine_comment(connection=connection, external_id=ticket.external_id, comment=comment)
            elif connection.tool_name.lower() == "zoho":
                return await self._add_zoho_comment(connection=connection, external_id=ticket.external_id, comment=comment)
            elif connection.tool_name.lower() == "servicenow":
                return await self._add_servicenow_comment(connection=connection, external_id=ticket.external_id, comment=comment)
            else:
                logger.warning(f"Ticketing tool {connection.tool_name} not supported for comments")
                return False
        except Exception as e:
            logger.error(f"Error adding comment to ticket {ticket.id} in external system: {e}", exc_info=True)
            return False
        finally:
            ticket.external_ticket_updated_at = datetime.now(timezone.utc)
            db.commit()

    async def _add_manageengine_comment(
        self,
        connection: TicketingToolConnection,
        external_id: str,
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

            api_domain = connection.api_base_url or connection_meta.get("api_domain", "")
            if not api_domain.startswith("http"):
                api_domain = f"https://{api_domain}"

            comment_url = f"{api_domain}/api/v3/tickets/{external_id}/comments"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(comment_url, headers=headers, json={"content": comment, "isPublic": True})
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
                "orgId": org_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(comment_url, headers=headers, json={"content": comment, "isPublic": True})
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
        comment: str,
    ) -> bool:
        try:
            import httpx

            connection_meta = (
                json.loads(connection.meta_data) if isinstance(connection.meta_data, str) else
                (connection.meta_data if isinstance(connection.meta_data, dict) else {})
            )

            api_base_url = connection.api_base_url or connection_meta.get("api_base_url", "")
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")

            username = connection_meta.get("username") or connection_meta.get("user")
            password = connection_meta.get("password")

            if not (username and password):
                logger.error("ServiceNow authentication credentials not found")
                return False

            auth_b64 = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Resolve incident number to sys_id if needed
            if not external_id.startswith("sys_"):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    query_response = await client.get(
                        f"{api_base_url}/api/now/table/incident",
                        headers=headers,
                        params={"sysparm_query": f"number={external_id}", "sysparm_fields": "sys_id"},
                    )
                    if query_response.status_code == 200:
                        result = query_response.json().get("result", [])
                        if result:
                            external_id = result[0]["sys_id"]
                        else:
                            logger.warning(f"ServiceNow incident {external_id} not found")
                            return False
                    else:
                        logger.error(f"Failed to query ServiceNow incident: {query_response.status_code}")
                        return False

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{api_base_url}/api/now/table/incident/{external_id}",
                    headers=headers,
                    json={"comments": comment},
                )
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully added comment to ServiceNow incident {external_id}")
                    return True
                else:
                    logger.error(f"Failed to add comment to ServiceNow incident: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error adding ServiceNow comment: {e}", exc_info=True)
            return False
