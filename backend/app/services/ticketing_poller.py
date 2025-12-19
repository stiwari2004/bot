"""
Ticketing Poller Service
Background service that polls ticketing tools for new tickets
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.models.ticket import Ticket
from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketingPoller:
    """Background service for polling ticketing tools"""
    
    def __init__(self):
        self.zoho_fetcher = ZohoTicketFetcher()
        self.manageengine_fetcher = ManageEngineTicketFetcher()
        self.servicenow_fetcher = ServiceNowTicketFetcher()
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the polling service"""
        if self.running:
            logger.warning("Polling service is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Ticketing poller service started")
    
    async def stop(self):
        """Stop the polling service"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                # Wait for task to cancel with timeout
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.warning(f"Error waiting for polling task to stop: {e}")
        
        try:
            await self.zoho_fetcher.close()
            await self.manageengine_fetcher.close()
            await self.servicenow_fetcher.close()
        except Exception as e:
            logger.warning(f"Error closing fetchers: {e}")
        
        logger.info("Ticketing poller service stopped")
    
    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                await self._poll_all_connections()
                
                # Sleep for 1 minute before next iteration, but check running status frequently
                # Individual connections have their own sync intervals
                for _ in range(60):  # Check every second instead of sleeping 60 seconds
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                # Shorter sleep on error, but still check running status
                for _ in range(10):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
    
    async def _poll_all_connections(self):
        """Poll all active API polling connections"""
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Get all active API polling connections for all tenants
            connections = db.query(TicketingToolConnection).filter(
                TicketingToolConnection.is_active == True,
                TicketingToolConnection.connection_type == "api_poll"
            ).all()
            
            for connection in connections:
                try:
                    # Check if it's time to sync this connection
                    if not self._should_sync(connection):
                        continue
                    
                    await self._poll_connection(connection, db)
                    
                except Exception as e:
                    logger.error(f"Error polling connection {connection.id} ({connection.tool_name}): {e}")
                    try:
                        connection.last_sync_status = "failed"
                        connection.last_error = str(e)
                        db.commit()
                    except Exception:
                        db.rollback()
                    continue
        except Exception as e:
            logger.error(f"Error polling connections: {e}")
        finally:
            db.close()
    
    def _should_sync(self, connection: TicketingToolConnection) -> bool:
        """Check if connection should be synced based on sync interval"""
        if not connection.last_sync_at:
            return True
        
        # Default to 1 minute for near real-time updates (was 5 minutes)
        interval_minutes = connection.sync_interval_minutes or 1
        
        # Ensure last_sync_at is timezone-aware
        last_sync = connection.last_sync_at
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=timezone.utc)
        
        next_sync = last_sync + timedelta(minutes=interval_minutes)
        now = datetime.now(timezone.utc)  # Use timezone-aware datetime
        return now >= next_sync
    
    async def _poll_connection(self, connection: TicketingToolConnection, db: Session):
        """Poll a single connection for tickets"""
        logger.info(f"Polling {connection.tool_name} connection {connection.id}")
        
        # Track if tokens were refreshed (so we can persist them even if fetch fails)
        tokens_refreshed = False
        original_meta_data = None
        
        try:
            meta_data = json.loads(connection.meta_data) if connection.meta_data else {}
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
                # ManageEngine now uses OAuth 2.0 (same as Zoho)
                tickets = await self.manageengine_fetcher.fetch_tickets(
                    api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                    connection_meta=meta_data,
                    since=since,
                    limit=100
                )
            
            elif connection.tool_name == "servicenow":
                # ServiceNow supports OAuth 2.0 or Basic Auth
                logger.info(f"Fetching ServiceNow tickets: since={since}, limit=100")
                logger.debug(f"ServiceNow meta_data keys: {list(meta_data.keys())}")
                # Credentials can be in meta_data OR in connection.api_username/api_password
                # Check both locations
                username = meta_data.get("username") or connection.api_username
                password = meta_data.get("password") or connection.api_password
                logger.debug(f"ServiceNow credentials: username={'present' if username else 'missing'}, password={'present' if password else 'missing'}")
                if username:
                    logger.debug(f"ServiceNow username (first 5 chars): {username[:5]}... (length: {len(username)})")
                if password:
                    logger.debug(f"ServiceNow password length: {len(password)} chars")
                tickets = await self.servicenow_fetcher.fetch_tickets(
                    api_base_url=connection.api_base_url or meta_data.get("api_base_url", ""),
                    connection_meta=meta_data,
                    username=username,
                    password=password,
                    client_id=meta_data.get("client_id"),
                    client_secret=meta_data.get("client_secret"),
                    since=since,
                    limit=100
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
                        # Note: json is already imported at the top of the file
                        
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
            logger.error(f"Error polling {connection.tool_name} connection {connection.id}: {e}", exc_info=True)
            
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


# Global poller instance
_poller: Optional[TicketingPoller] = None


async def start_poller():
    """Start the global polling service"""
    global _poller
    if _poller is None:
        _poller = TicketingPoller()
        await _poller.start()


async def stop_poller():
    """Stop the global polling service"""
    global _poller
    if _poller:
        await _poller.stop()
        _poller = None

