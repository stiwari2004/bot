"""
Recurring incident detection service (MVP).

Adds simple recurring metadata to tickets when multiple incidents
occur for the same service/environment within a recent time window.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.core.logging import get_logger


logger = get_logger(__name__)


def update_recurring_metadata(
    db: Session,
    ticket: Ticket,
    *,
    window_hours: int = 24,
    threshold: int = 3,
) -> None:
    """
    Mark a ticket as part of a recurring incident group if enough
    similar tickets exist in a recent time window.

    MVP rules:
    - Group by tenant_id + service + environment
    - Look back over the last `window_hours`
    - If count >= `threshold`, attach `meta_data['recurring']`
      with group_key and count.
    """
    try:
        if not ticket.service or not ticket.environment:
            return

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=window_hours)

        # Count tickets in same tenant/service/environment within window
        # including the current one (which is not yet committed but present in session).
        q = (
            db.query(Ticket)
            .filter(
                Ticket.tenant_id == ticket.tenant_id,
                Ticket.service == ticket.service,
                Ticket.environment == ticket.environment,
                Ticket.created_at >= cutoff,
            )
        )

        count = q.count()
        if count < threshold:
            # Not yet considered "recurring"
            return

        group_key = f"{ticket.tenant_id}:{ticket.service}:{ticket.environment}"

        meta = ticket.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}

        recurring = meta.get("recurring", {}) or {}
        recurring.update(
            {
                "group_key": group_key,
                "count": count,
                "window_hours": window_hours,
                "threshold": threshold,
            }
        )
        meta["recurring"] = recurring
        ticket.meta_data = meta

        logger.info(
            f"Ticket {ticket.id} marked as recurring incident: "
            f"group={group_key}, count={count}"
        )
    except Exception as e:
        logger.warning(f"Failed to update recurring metadata for ticket {ticket.id}: {e}")

