"""
ChangeWindowMonitor — background service that retriggers suppressed sessions
when their change window expires and the alert is still firing.

Lifecycle:
  - start_monitor() is called from app/main.py lifespan startup
  - stop_monitor() is called from app/main.py lifespan shutdown

Interval is controlled by the CHANGE_WINDOW_MONITOR_INTERVAL env var
(seconds, default 300 = 5 minutes).

What it does each tick:
  1. Calls ChangeWindowService.retrigger_expired_suppressions()
  2. That method scans suppressed tickets whose change window has ended
  3. For each: checks if the alert is still firing in the Alert table
       - Still firing  → creates a new session referencing the original
                         suppressed session and fires the agent executor
       - Resolved      → closes the ticket ("resolved during change window")
"""
import asyncio
import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_INTERVAL_S = 300   # 5 minutes
_monitor_task: Optional[asyncio.Task] = None


async def _monitor_loop(interval: int) -> None:
    logger.info("Change window monitor started (interval=%ds)", interval)
    while True:
        await asyncio.sleep(interval)
        from app.core.database import SessionLocal
        from app.services.change_window_service import get_change_window_service

        db = SessionLocal()
        try:
            count = await get_change_window_service().retrigger_expired_suppressions(db)
            if count:
                logger.info(
                    "Change window monitor: %d session(s) retriggered after window expiry", count
                )
        except Exception as exc:
            logger.exception("Change window monitor error: %s", exc)
        finally:
            db.close()


async def start_monitor() -> None:
    global _monitor_task
    interval = int(os.getenv("CHANGE_WINDOW_MONITOR_INTERVAL", str(_DEFAULT_INTERVAL_S)))
    _monitor_task = asyncio.create_task(_monitor_loop(interval))
    logger.info("Change window monitor task created (interval=%ds)", interval)


async def stop_monitor() -> None:
    global _monitor_task
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await asyncio.wait_for(_monitor_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        _monitor_task = None
    logger.info("Change window monitor stopped")
