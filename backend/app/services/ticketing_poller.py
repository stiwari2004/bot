"""
Ticketing Poller Service
Background service that polls ticketing tools for new tickets
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.services.ticketing_connectors.zoho import ZohoTicketFetcher
from app.services.ticketing_connectors.manageengine import ManageEngineTicketFetcher
from app.services.ticketing_connectors.servicenow import ServiceNowTicketFetcher
from app.core.logging import get_logger
from app.services.ticketing_poller_connection_mixin import TicketingPollerConnectionMixin

logger = get_logger(__name__)


class TicketingPoller(TicketingPollerConnectionMixin):
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
    
    # _poll_connection - now provided by TicketingPollerConnectionMixin


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

