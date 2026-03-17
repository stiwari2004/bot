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
from app.services.ticketing_connectors.servicenow_auth_mixin import ServiceNowAuthMixin

logger = get_logger(__name__)


class ServiceNowTicketFetcher(ServiceNowAuthMixin):
    """Fetches incidents from ServiceNow"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

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
        """Fetch incidents from ServiceNow"""
        try:
            if not api_base_url.startswith("http"):
                api_base_url = f"https://{api_base_url}"
            api_base_url = api_base_url.rstrip("/")

            final_username = username if username and username.strip() else connection_meta.get("username")
            final_password = password if password and password.strip() else connection_meta.get("password")
            final_client_id = client_id if client_id and client_id.strip() else connection_meta.get("client_id")
            final_client_secret = client_secret if client_secret and client_secret.strip() else connection_meta.get("client_secret")

            logger.info(f"ServiceNow fetch_tickets - final credentials: username={'present' if final_username else 'missing'}, password={'present' if final_password else 'missing'}")
            if final_username:
                logger.info(f"🔍 ServiceNow username value: {final_username[:10]}... (length: {len(final_username)})")
            if final_password:
                logger.info(f"🔍 ServiceNow password length: {len(final_password)} chars, first 5 chars: {final_password[:5]}...")

            basic_auth_username = None
            basic_auth_password = None

            if final_username and final_password and final_username.strip() and final_password.strip():
                basic_auth_username = final_username.strip()
                basic_auth_password = final_password.strip()
                logger.info(f"Using credentials from parameters: username length={len(basic_auth_username)}, password length={len(basic_auth_password)}")
            elif connection_meta.get("username") and connection_meta.get("password"):
                meta_user = connection_meta.get("username")
                meta_pass = connection_meta.get("password")
                logger.info(f"Found credentials in meta_data: username type={type(meta_user).__name__}, password type={type(meta_pass).__name__}")
                if isinstance(meta_user, str) and isinstance(meta_pass, str) and meta_user.strip() and meta_pass.strip():
                    basic_auth_username = meta_user.strip()
                    basic_auth_password = meta_pass.strip()
                    logger.info(f"✅ Using credentials from meta_data: username length={len(basic_auth_username)}, password length={len(basic_auth_password)}")
                else:
                    logger.warning(f"⚠️ Meta credentials exist but invalid: username is_str={isinstance(meta_user, str)}, password is_str={isinstance(meta_pass, str)}")
            else:
                logger.warning(f"⚠️ No credentials in connection_meta: username={'present' if connection_meta.get('username') else 'missing'}, password={'present' if connection_meta.get('password') else 'missing'}")

            if basic_auth_username and basic_auth_password:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                credentials = f"{basic_auth_username}:{basic_auth_password}"
                logger.info(f"Credentials string (first 20 chars): {credentials[:20]}... (full length: {len(credentials)})")
                encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                auth_header = f"Basic {encoded}"
                headers["Authorization"] = auth_header
                logger.info(f"Authorization header (base64 encoded): {auth_header[:50]}... (full length: {len(auth_header)})")
                logger.info(f"Username: {basic_auth_username}, Password length: {len(basic_auth_password)} chars")
                logger.info(f"Base64 encoded value: {encoded[:50]}... (full length: {len(encoded)})")
                auth = None
            else:
                logger.warning("ServiceNow: No credentials found - request will likely get 401")
                auth = None
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }

            api_url = f"{api_base_url}/api/now/table/incident"

            params = {
                "sysparm_limit": min(limit, 100),
                "sysparm_orderby": "sys_updated_on:desc",
                "sysparm_display_value": "true"
            }

            if status_filter:
                params["sysparm_query"] = f"stateIN{','.join(status_filter)}"

            if since:
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
                since_str = since.strftime("%Y-%m-%d")
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
                    logger.info(f"Authorization header present (length: {len(headers['Authorization'])})")
                else:
                    logger.warning("Authorization header missing from headers dict")

                response = await self.client.get(api_url, headers=headers, params=params)
                if response.status_code == 401:
                    logger.error(f"401 Response body: {response.text[:200]}")
                logger.debug(f"ServiceNow API response status: {response.status_code}")

                content_type = response.headers.get("Content-Type", "").lower()
                response_text = response.text

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

                if not response_text or not response_text.strip():
                    logger.error(f"ServiceNow API returned empty response (status: {response.status_code})")
                    raise Exception(f"ServiceNow API returned empty response (status: {response.status_code})")

                response.raise_for_status()

                try:
                    data = response.json()
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to parse ServiceNow JSON response: {e}")
                    logger.error(f"Content-Type: {content_type}")
                    logger.error(f"Response text (first 500 chars): {response_text[:500]}")
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

                for incident in incidents:
                    normalized = self._normalize_ticket(incident)
                    all_tickets.append(normalized)
                    logger.debug(f"Normalized ServiceNow incident: {normalized.get('external_id')} - {normalized.get('title')}")

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

        state_map = {
            "1": "open", "2": "in_progress", "3": "open",
            "4": "resolved", "5": "resolved", "6": "resolved"
        }
        normalized_status = state_map.get(str(state), "open")

        priority_map = {
            "1": "critical", "2": "high", "3": "medium", "4": "low", "5": "low"
        }
        severity = priority_map.get(str(priority), "medium")

        if severity == "medium" and urgency:
            urgency_map = {
                "1": "critical", "2": "high", "3": "medium", "4": "low", "5": "low"
            }
            severity = urgency_map.get(str(urgency), "medium")

        return {
            "external_id": str(number or sys_id),
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
