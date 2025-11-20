"""
Service for cleaning up ticket references when runbooks are deleted
"""
from typing import List
from sqlalchemy.orm import Session
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
            if ticket.meta_data and isinstance(ticket.meta_data, dict):
                updated = False
                
                # Remove from matched_runbooks if present
                if "matched_runbooks" in ticket.meta_data:
                    if isinstance(ticket.meta_data["matched_runbooks"], list):
                        original_count = len(ticket.meta_data["matched_runbooks"])
                        ticket.meta_data["matched_runbooks"] = [
                            rb for rb in ticket.meta_data["matched_runbooks"]
                            if isinstance(rb, dict) and rb.get("id") != runbook_id
                        ]
                        if len(ticket.meta_data["matched_runbooks"]) < original_count:
                            updated = True
                
                # Remove from any other runbook references
                if "runbook_id" in ticket.meta_data and ticket.meta_data["runbook_id"] == runbook_id:
                    del ticket.meta_data["runbook_id"]
                    updated = True
                
                if updated:
                    # Update the ticket's meta_data
                    ticket.meta_data = ticket.meta_data  # Trigger SQLAlchemy to detect change
                    updated_count += 1
        
        if updated_count > 0:
            db.commit()
            logger.info(f"Cleaned up runbook {runbook_id} references from {updated_count} tickets")
        
        return updated_count




