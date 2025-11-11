"""
Ticket Status Service - Update ticket status based on execution lifecycle
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession
from datetime import datetime
from typing import Optional

logger = get_logger(__name__)


class TicketStatusService:
    """Service for managing ticket status updates"""
    
    def update_ticket_on_execution_start(self, db: Session, ticket_id: int) -> Optional[Ticket]:
        """Update ticket status to 'in_progress' when execution starts"""
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for status update")
                return None
            
            if ticket.status != "closed":  # Don't update if already closed
                ticket.status = "in_progress"
                ticket.updated_at = datetime.now()
                db.commit()
                db.refresh(ticket)
                logger.info(f"Ticket {ticket_id} status updated to 'in_progress'")
            
            return ticket
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id} status to in_progress: {e}")
            db.rollback()
            return None
    
    def update_ticket_on_execution_complete(
        self, 
        db: Session, 
        ticket_id: int, 
        execution_status: str,
        issue_resolved: Optional[bool] = None
    ) -> Optional[Ticket]:
        """
        Update ticket status based on execution completion
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            execution_status: 'completed', 'failed', 'rejected', 'abandoned'
            issue_resolved: Whether the issue was actually resolved (optional)
        """
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for status update")
                return None
            
            # Determine ticket status based on execution result
            if execution_status == "completed":
                if issue_resolved is True:
                    ticket.status = "resolved"
                    ticket.resolved_at = datetime.now()
                elif issue_resolved is False:
                    ticket.status = "escalated"
                else:
                    # If resolution status unknown, mark as in_progress for manual review
                    ticket.status = "in_progress"
            
            elif execution_status == "failed":
                ticket.status = "escalated"
            
            elif execution_status == "rejected":
                ticket.status = "in_progress"  # Keep as in_progress for retry
            
            elif execution_status == "abandoned":
                ticket.status = "escalated"  # Escalate if abandoned
            
            ticket.updated_at = datetime.now()
            db.commit()
            db.refresh(ticket)
            
            logger.info(f"Ticket {ticket_id} status updated to '{ticket.status}' (execution: {execution_status})")
            return ticket
            
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id} status: {e}")
            db.rollback()
            return None
    
    def update_ticket_on_false_positive(self, db: Session, ticket_id: int) -> Optional[Ticket]:
        """Update ticket status to 'closed' when false positive detected"""
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for status update")
                return None
            
            ticket.status = "closed"
            ticket.resolved_at = datetime.now()
            ticket.updated_at = datetime.now()
            db.commit()
            db.refresh(ticket)
            
            logger.info(f"Ticket {ticket_id} status updated to 'closed' (false positive)")
            return ticket
            
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id} status to closed: {e}")
            db.rollback()
            return None
    
    def get_ticket_status(self, db: Session, ticket_id: int) -> Optional[str]:
        """Get current ticket status"""
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            return ticket.status if ticket else None
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id} status: {e}")
            return None


# Global instance
_ticket_status_service: Optional[TicketStatusService] = None


def get_ticket_status_service() -> TicketStatusService:
    """Get or create ticket status service instance"""
    global _ticket_status_service
    if _ticket_status_service is None:
        _ticket_status_service = TicketStatusService()
    return _ticket_status_service




