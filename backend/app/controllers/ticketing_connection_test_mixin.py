"""
Mixin: ticketing connection test and sync operations
"""
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketingConnectionTestMixin:
    """Test and sync operations for TicketingConnectionController."""

    async def test_connection(self, connection_id: int) -> dict:
        db = self.db
        connection = self._fetch(connection_id)
        meta_data = self._parse_meta_data(connection.meta_data)

        if connection.tool_name in ("zoho", "manageengine"):
            requires_oauth = connection.tool_name == "zoho" or str(meta_data.get("version", "v2")).lower() == "v2"
            if requires_oauth and not meta_data.get("access_token"):
                return {
                    "status": "oauth_required",
                    "message": "OAuth authorization required. Please use the authorize endpoint first."
                }

        tickets_fetched = 0
        try:
            if connection.tool_name == "zoho":
                tickets_fetched = await self._test_zoho(connection, meta_data)
            elif connection.tool_name == "manageengine":
                tickets_fetched = await self._test_manageengine(connection, meta_data)
            elif connection.tool_name == "servicenow":
                tickets_fetched = await self._test_servicenow(connection, meta_data, db)
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error fetching tickets during test: {e}")
            connection.last_sync_at = datetime.utcnow()
            connection.last_sync_status = "error"
            connection.last_error = error_message
            db.commit()
            return {"status": "error", "message": f"Connection test failed: {error_message}", "tickets_fetched": 0}

        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = "success"
        connection.last_error = None
        db.commit()
        return {
            "status": "success",
            "message": f"Connection test successful. Fetched {tickets_fetched} tickets.",
            "tickets_fetched": tickets_fetched,
        }

    async def sync_connection(self, connection_id: int) -> dict:
        from app.services.ticketing_poller import TicketingPoller
        db = self.db
        connection = self._fetch(connection_id)

        if not connection.is_active:
            raise HTTPException(status_code=400, detail="Connection is not active")
        if connection.connection_type != "api_poll":
            raise HTTPException(status_code=400, detail="Manual sync only available for api_poll connections")

        logger.info(f"Manual sync triggered for {connection.tool_name} connection {connection_id}")
        poller = TicketingPoller()
        await poller._poll_connection(connection, db)
        db.refresh(connection)

        return {
            "status": "success",
            "message": f"Sync completed for {connection.tool_name} connection",
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status,
        }

    async def _test_zoho(self, connection, meta_data) -> int:
        from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
        fetcher = ZohoTicketFetcher()
        try:
            tickets = await fetcher.fetch_tickets(
                connection_meta=meta_data, api_base_url=connection.api_base_url, since=None, limit=10
            )
            return len(tickets)
        finally:
            await fetcher.close()

    async def _test_manageengine(self, connection, meta_data) -> int:
        from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
        fetcher = ManageEngineTicketFetcher()
        version = str(meta_data.get("version", "v2")).lower()
        test_since = None if version == "v3" else datetime.utcnow() - timedelta(days=7)
        try:
            tickets = await fetcher.fetch_tickets(
                api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                connection_meta=meta_data,
                api_key=connection.api_key,
                api_username=connection.api_username,
                api_password=connection.api_password,
                since=test_since,
                limit=10,
            )
            return len(tickets)
        finally:
            await fetcher.close()

    async def _test_servicenow(self, connection, meta_data, db) -> int:
        from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
        self._sync_servicenow_credentials(connection, meta_data)
        username = meta_data.get("username") or connection.api_username
        password = meta_data.get("password") or connection.api_password

        if not username or not password:
            raise ValueError(
                "ServiceNow credentials (username/password) are required for Basic Auth. "
                "Please update the connection with valid credentials."
            )

        fetcher = ServiceNowTicketFetcher()
        try:
            tickets = await fetcher.fetch_tickets(
                api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                connection_meta=meta_data,
                username=username,
                password=password,
                client_id=meta_data.get("client_id"),
                client_secret=meta_data.get("client_secret"),
                since=None,
                limit=10,
            )
            return len(tickets)
        finally:
            await fetcher.close()
