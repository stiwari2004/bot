"""
Mixin: _poll_connection implementation for TicketingPoller
"""
import json
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.models.ticket import Ticket
from app.services.change_window_service import get_change_window_service
from app.services.change_ticket_sync_service import get_change_ticket_sync_service
from app.services.recurring_incident_service import update_recurring_metadata
from app.core.logging import get_logger

logger = get_logger(__name__)


def _parse_connection_meta_safe(raw) -> Dict[str, Any]:
    """Parse connection meta_data to a dict; never raise. Handles None, empty string, 'null', invalid JSON."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid ticketing connection meta_data JSON in poller, using empty dict")
        return {}


class TicketingPollerConnectionMixin:
    """_poll_connection implementation for TicketingPoller."""

    async def _poll_connection(self, connection: TicketingToolConnection, db: Session):
        """Poll a single connection for tickets"""
        logger.info(f"Polling {connection.tool_name} connection {connection.id}")

        # First, try to sync change tickets for tools that support it (ServiceNow, ManageEngine).
        try:
            if connection.tool_name in ("servicenow", "manageengine"):
                change_sync_service = get_change_ticket_sync_service()
                sync_stats = await change_sync_service.sync_change_tickets(
                    connection, db
                )
                logger.info(
                    f"Change ticket sync for {connection.tool_name} connection {connection.id}: "
                    f"{sync_stats.get('created_count', 0)} created, "
                    f"{sync_stats.get('updated_count', 0)} updated, "
                    f"{sync_stats.get('error_count', 0)} errors"
                )
                # After syncing changes, auto-unsuppress any tickets whose change windows have expired.
                try:
                    change_window_service = get_change_window_service()
                    unsuppressed = change_window_service.auto_unsuppress_expired_changes(
                        db, tenant_id=connection.tenant_id
                    )
                    if unsuppressed:
                        logger.info(
                            f"Auto-unsuppressed {unsuppressed} tickets for tenant "
                            f"{connection.tenant_id} after change window updates"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to auto-unsuppress tickets after change sync: {e}"
                    )
        except Exception as e:
            logger.error(
                f"Error during change ticket sync for {connection.tool_name} connection "
                f"{connection.id}: {e}",
                exc_info=True,
            )

        # Track if tokens were refreshed (so we can persist them even if fetch fails)
        tokens_refreshed = False
        original_meta_data = None

        try:
            meta_data = _parse_connection_meta_safe(connection.meta_data)
            # Store original to detect if tokens changed
            original_meta_data = json.dumps(meta_data) if meta_data else None

            # Determine last sync time
            # For first sync or if last_sync_at is None, fetch all recent tickets (last 24 hours)
            # For subsequent syncs, only fetch tickets updated since last sync
            since = None
            if connection.last_sync_at:
                since = connection.last_sync_at
                # Ensure since is timezone-aware
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
                # If last sync was more than 24 hours ago, limit to last 24 hours to avoid huge fetches
                time_since_last_sync = datetime.now(timezone.utc) - since
                if time_since_last_sync > timedelta(hours=24):
                    since = datetime.now(timezone.utc) - timedelta(hours=24)
                    logger.info(f"Last sync was {time_since_last_sync} ago, limiting fetch to last 24 hours")
            else:
                # First sync - fetch tickets from last 24 hours
                since = datetime.now(timezone.utc) - timedelta(hours=24)
                logger.info(f"First sync for {connection.tool_name} connection {connection.id}, fetching tickets from last 24 hours")

            tickets = []

            if connection.tool_name == "zoho":
                tickets = await self.zoho_fetcher.fetch_tickets(
                    connection_meta=meta_data,
                    api_base_url=connection.api_base_url,
                    since=since,
                    limit=100
                )

            elif connection.tool_name == "manageengine":
                # ManageEngine supports:
                # - v2: OAuth 2.0 (authorization code flow, same as Zoho)
                # - v3: API key/authtoken
                # On this SDP instance, v3/authtoken rejects list_info.search_criteria,
                # so for v3 we avoid date-based filtering and rely on our own de-duplication.
                version = str(meta_data.get("version", "v2")).lower()
                effective_since = since
                if version == "v3":
                    effective_since = None
                    logger.info(
                        f"ManageEngine v3 connection {connection.id}: disabling server-side "
                        f"search_criteria; fetching latest tickets without since filter."
                    )
                tickets = await self.manageengine_fetcher.fetch_tickets(
                    api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                    connection_meta=meta_data,
                    api_key=connection.api_key,
                    api_username=connection.api_username,
                    api_password=connection.api_password,
                    since=effective_since,
                    limit=100
                )

            elif connection.tool_name == "servicenow":
                # ServiceNow supports OAuth 2.0 or Basic Auth
                # Fetch tickets by status (not by date): exclude resolved/closed/canceled
                # ServiceNow states: 1=New, 2=In Progress, 3=On Hold, 4=Resolved, 5=Closed, 6=Canceled
                # We want states 1, 2, 3 (active tickets)
                status_filter = ["1", "2", "3"]  # New, In Progress, On Hold
                logger.info(f"Fetching ServiceNow tickets: status_filter={status_filter}, limit=100 (excluding resolved/closed/canceled)")
                logger.debug(f"ServiceNow meta_data keys: {list(meta_data.keys())}")

                # Sync credentials from connection fields to meta_data if missing (for backward compatibility)
                synced = False
                if not meta_data.get("username") and connection.api_username:
                    meta_data["username"] = connection.api_username
                    synced = True
                if not meta_data.get("password") and connection.api_password:
                    meta_data["password"] = connection.api_password
                    synced = True
                # If we synced, save it back to DB
                if synced:
                    connection.meta_data = json.dumps(meta_data)
                    db.commit()
                    logger.info(f"Synced ServiceNow credentials from connection fields to meta_data for connection {connection.id}")

                # Credentials can be in meta_data OR in connection.api_username/api_password
                # Check both locations
                username = meta_data.get("username") or connection.api_username
                password = meta_data.get("password") or connection.api_password
                logger.info(f"ServiceNow poller - credentials check: username={'present' if username else 'missing'}, password={'present' if password else 'missing'}")
                logger.info(f"ServiceNow poller - api_username: {'present' if connection.api_username else 'missing'}, api_password: {'present' if connection.api_password else 'missing'}")
                logger.info(f"ServiceNow poller - meta_data keys: {list(meta_data.keys())}")
                if username:
                    logger.info(f"ServiceNow username (first 5 chars): {username[:5]}... (length: {len(username)})")
                if password:
                    logger.info(f"ServiceNow password length: {len(password)} chars")

                if not username or not password:
                    error_msg = (
                        f"ServiceNow connection {connection.id} missing credentials. "
                        f"api_username: {'set' if connection.api_username else 'missing'}, "
                        f"api_password: {'set' if connection.api_password else 'missing'}, "
                        f"meta_data.username: {'set' if meta_data.get('username') else 'missing'}, "
                        f"meta_data.password: {'set' if meta_data.get('password') else 'missing'}"
                    )
                    logger.error(f"❌ {error_msg}")
                    raise ValueError("ServiceNow credentials (username/password) are required for Basic Auth. Please update the connection with valid credentials.")

                tickets = await self.servicenow_fetcher.fetch_tickets(
                    api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                    connection_meta=meta_data,
                    username=username,
                    password=password,
                    client_id=meta_data.get("client_id"),
                    client_secret=meta_data.get("client_secret"),
                    status_filter=status_filter,
                    limit=100,
                    since=None  # Don't use date filter - fetch all active tickets
                )
                logger.info(f"ServiceNow fetcher returned {len(tickets)} tickets")

            else:
                logger.warning(f"Unsupported tool for polling: {connection.tool_name}")
                return

            # Check if tokens were refreshed (meta_data changed)
            current_meta_data = json.dumps(meta_data) if meta_data else None
            if current_meta_data != original_meta_data:
                tokens_refreshed = True
                logger.info(f"Tokens were refreshed for {connection.tool_name} connection {connection.id}")

            # Create/update tickets in database
            created_count = 0
            updated_count = 0
            error_count = 0

            logger.info(f"Processing {len(tickets)} tickets from {connection.tool_name} connection {connection.id}")

            if len(tickets) == 0:
                logger.warning(f"No tickets fetched from {connection.tool_name} connection {connection.id}. This could mean:")
                logger.warning(f"  1. No tickets match the query criteria (since={since})")
                logger.warning(f"  2. API returned empty result")
                logger.warning(f"  3. Authentication/authorization issue")

            for ticket_data in tickets:
                try:
                    external_id = ticket_data.get("external_id")
                    title = ticket_data.get("title", "No title")
                    source = ticket_data.get("source")

                    logger.debug(f"Processing ticket: external_id={external_id}, source={source}, title={title[:50]}")

                    # Check if ticket already exists by external_id
                    existing = db.query(Ticket).filter(
                        Ticket.tenant_id == connection.tenant_id,
                        Ticket.source == source,
                        Ticket.external_id == external_id
                    ).first()

                    if existing:
                        # Update existing ticket
                        logger.debug(f"Ticket {external_id} already exists, updating...")
                        # CRITICAL: Preserve existing meta_data (including matched_runbooks) when syncing from external system
                        from sqlalchemy.orm.attributes import flag_modified

                        # Preserve existing meta_data
                        if existing.meta_data:
                            preserved_meta = dict(existing.meta_data) if isinstance(existing.meta_data, dict) else json.loads(existing.meta_data) if isinstance(existing.meta_data, str) else {}
                        else:
                            preserved_meta = {}

                        # Merge external metadata (from ticketing system) into preserved metadata
                        external_meta = ticket_data.get("metadata", {})
                        if external_meta:
                            # Merge external metadata, but don't overwrite critical fields like matched_runbooks
                            for key, value in external_meta.items():
                                if key not in ["matched_runbooks"]:  # Preserve matched_runbooks
                                    preserved_meta[key] = value

                        existing.title = ticket_data["title"]
                        existing.description = ticket_data["description"]
                        existing.severity = ticket_data["severity"]
                        existing.status = ticket_data["status"]
                        existing.meta_data = preserved_meta
                        flag_modified(existing, "meta_data")
                        updated_count += 1
                        logger.debug(f"Updated ticket {external_id}")
                    else:
                        # Create new ticket
                        logger.info(f"Creating new ticket: external_id={external_id}, title={title[:50]}")
                        new_ticket = Ticket(
                            tenant_id=connection.tenant_id,
                            source=source,
                            external_id=external_id,
                            title=ticket_data["title"],
                            description=ticket_data["description"],
                            severity=ticket_data["severity"],
                            status=ticket_data["status"],
                            environment=ticket_data.get("environment", "prod"),  # Default to "prod" if not specified
                            service=ticket_data.get("service"),  # Optional
                            meta_data=ticket_data.get("metadata", {}),
                            received_at=datetime.now(timezone.utc)
                        )
                        db.add(new_ticket)
                        db.flush()  # Flush to get ticket ID
                        created_count += 1
                        logger.info(f"✅ Created ticket: {external_id} - {title[:50]}")

                        # Check if ticket should be suppressed due to change window
                        try:
                            change_window_service = get_change_window_service()
                            change_window_service.check_and_suppress_ticket(db, new_ticket)
                        except Exception as e:
                            logger.warning(f"Failed to check ticket suppression: {e}")

                        # Update recurring incident metadata (MVP)
                        try:
                            update_recurring_metadata(db, new_ticket)
                        except Exception as e:
                            logger.warning(f"Failed to update recurring metadata: {e}")

                        # Track billing: ticket received
                        try:
                            from app.services.billing.billing_tracker import BillingTracker
                            tracker = BillingTracker(db)
                            tracker.track_ticket_received(connection.tenant_id, new_ticket.id)
                        except Exception as e:
                            logger.warning(f"Failed to track ticket received for billing: {e}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error processing ticket {ticket_data.get('external_id')}: {e}", exc_info=True)
                    continue

            logger.info(f"Ticket processing complete: {created_count} created, {updated_count} updated, {error_count} errors")

            # Update connection metadata if tokens were refreshed (for Zoho, ManageEngine, and ServiceNow)
            # Always persist tokens if they were refreshed, even if fetch_tickets() succeeded
            if connection.tool_name in ("zoho", "manageengine", "servicenow") and meta_data:
                connection.meta_data = json.dumps(meta_data)
                if tokens_refreshed:
                    logger.info(f"Persisted refreshed tokens for {connection.tool_name} connection {connection.id}")
                else:
                    logger.debug(f"Persisted tokens for {connection.tool_name} connection {connection.id}")

            # Update connection sync status
            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = "success"
            connection.last_error = None

            db.commit()

            logger.info(
                f"Polled {connection.tool_name} connection {connection.id}: "
                f"{created_count} created, {updated_count} updated"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error polling {connection.tool_name} connection {connection.id}: {error_msg}", exc_info=True)

            # Check if it's a ServiceNow hibernation error - handle more gracefully
            if connection.tool_name == "servicenow" and "hibernat" in error_msg.lower():
                logger.warning(
                    f"ServiceNow connection {connection.id} instance is hibernated. "
                    "Skipping this polling cycle. Connection will be retried on next cycle."
                )
                # Mark as error but don't raise - allow other connections to continue
                connection.last_sync_status = "error"
                connection.last_error = "Instance hibernated - will retry on next poll"
                db.commit()
                return  # Skip this connection, continue with others

            # CRITICAL: Persist refreshed tokens even if fetch_tickets() failed
            # This ensures we don't lose refreshed tokens due to API errors
            if tokens_refreshed and connection.tool_name in ("zoho", "manageengine", "servicenow") and meta_data:
                try:
                    logger.warning(
                        f"Fetch failed but tokens were refreshed. Persisting tokens for {connection.tool_name} "
                        f"connection {connection.id} to prevent token loss."
                    )
                    connection.meta_data = json.dumps(meta_data)
                    # Also update sync status but mark as failed
                    connection.last_sync_at = datetime.now(timezone.utc)
                    connection.last_sync_status = "failed"
                    connection.last_error = str(e)[:500]  # Limit error length
                    db.commit()
                    logger.info(f"Successfully persisted refreshed tokens despite fetch failure")
                except Exception as persist_error:
                    logger.error(f"Failed to persist refreshed tokens after fetch error: {persist_error}", exc_info=True)
                    db.rollback()
            else:
                # No tokens refreshed, just update error status
                try:
                    connection.last_sync_at = datetime.now(timezone.utc)
                    connection.last_sync_status = "failed"
                    connection.last_error = str(e)[:500]  # Limit error length
                    db.commit()
                except Exception:
                    db.rollback()
            raise
