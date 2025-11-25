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
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketingPoller:
    """Background service for polling ticketing tools"""
    
    def __init__(self):
        self.zoho_fetcher = ZohoTicketFetcher()
        self.manageengine_fetcher = ManageEngineTicketFetcher()
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
            tenant_id = 1
            
            # Get all active API polling connections
            connections = db.query(TicketingToolConnection).filter(
                TicketingToolConnection.tenant_id == tenant_id,
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
        
        interval_minutes = connection.sync_interval_minutes or 5
        
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
            
            # Determine last sync time (default to 1 hour ago if never synced)
            since = None
            if connection.last_sync_at:
                since = connection.last_sync_at
                # Ensure since is timezone-aware
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
            else:
                since = datetime.now(timezone.utc) - timedelta(hours=1)
            
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
            
            for ticket_data in tickets:
                try:
                    # Check if ticket already exists by external_id
                    existing = db.query(Ticket).filter(
                        Ticket.tenant_id == connection.tenant_id,
                        Ticket.source == ticket_data["source"],
                        Ticket.external_id == ticket_data["external_id"]
                    ).first()
                    
                    if existing:
                        # Update existing ticket
                        existing.title = ticket_data["title"]
                        existing.description = ticket_data["description"]
                        existing.severity = ticket_data["severity"]
                        existing.status = ticket_data["status"]
                        existing.meta_data = ticket_data.get("metadata", {})
                        updated_count += 1
                    else:
                        # Create new ticket
                        new_ticket = Ticket(
                            tenant_id=connection.tenant_id,
                            source=ticket_data["source"],
                            external_id=ticket_data["external_id"],
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
                        created_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing ticket {ticket_data.get('external_id')}: {e}")
                    continue
            
            # Update connection metadata if tokens were refreshed (for Zoho and ManageEngine)
            # Always persist tokens if they were refreshed, even if fetch_tickets() succeeded
            if connection.tool_name in ("zoho", "manageengine") and meta_data:
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
            if tokens_refreshed and connection.tool_name in ("zoho", "manageengine") and meta_data:
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

