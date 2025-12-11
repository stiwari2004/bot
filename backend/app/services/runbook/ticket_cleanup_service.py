"""
Service for cleaning up ticket references when runbooks are deleted
"""
from typing import List
import json
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.ticket import Ticket
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketCleanupService:
    """Service for cleaning up ticket references to deleted runbooks"""
    
    def cleanup_runbook_references(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> int:
        """
        Remove references to a runbook from all tickets' meta_data.
        Returns the number of tickets updated.
        """
        tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.meta_data.isnot(None)
        ).all()
        
        updated_count = 0
        
        for ticket in tickets:
            # Parse meta_data if it's a string, otherwise use as dict
            if ticket.meta_data:
                if isinstance(ticket.meta_data, str):
                    try:
                        meta_data = json.loads(ticket.meta_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse meta_data for ticket {ticket.id}, skipping")
                        continue
                elif isinstance(ticket.meta_data, dict):
                    meta_data = dict(ticket.meta_data)  # Create a copy to modify
                else:
                    continue
            else:
                continue
            
            updated = False
            
            # Remove from matched_runbooks if present
            if "matched_runbooks" in meta_data:
                if isinstance(meta_data["matched_runbooks"], list):
                    original_count = len(meta_data["matched_runbooks"])
                    meta_data["matched_runbooks"] = [
                        rb for rb in meta_data["matched_runbooks"]
                        if isinstance(rb, dict) and rb.get("id") != runbook_id
                    ]
                    if len(meta_data["matched_runbooks"]) < original_count:
                        updated = True
                        logger.debug(f"Removed runbook {runbook_id} from ticket {ticket.id} matched_runbooks")
            
            # Remove from any other runbook references
            if "runbook_id" in meta_data and meta_data["runbook_id"] == runbook_id:
                del meta_data["runbook_id"]
                updated = True
                logger.debug(f"Removed runbook {runbook_id} from ticket {ticket.id} runbook_id")
            
            if updated:
                # Update the ticket's meta_data and flag it as modified
                ticket.meta_data = meta_data
                flag_modified(ticket, "meta_data")  # CRITICAL: Tell SQLAlchemy the JSON field changed
                updated_count += 1
        
        if updated_count > 0:
            try:
                db.commit()
                logger.info(f"Cleaned up runbook {runbook_id} references from {updated_count} tickets")
            except Exception as e:
                logger.error(f"Error committing cleanup for runbook {runbook_id}: {e}")
                db.rollback()
                raise
        
        return updated_count




