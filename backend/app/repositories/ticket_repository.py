"""
Repository for ticket data access
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.ticket import Ticket
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketRepository(BaseRepository[Ticket]):
    """Repository for ticket CRUD operations"""
    
    def __init__(self, db: Session):
        super().__init__(Ticket, db)
    
    def get_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Ticket]:
        """Get all tickets for a tenant, optionally filtered by status"""
        try:
            query = self.db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
            
            if status:
                # Handle comma-separated status values
                if ',' in status:
                    statuses = [s.strip() for s in status.split(',')]
                    query = query.filter(Ticket.status.in_(statuses))
                else:
                    query = query.filter(Ticket.status == status)
            
            return query.order_by(Ticket.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting tickets by tenant: {e}", exc_info=True)
            # Fallback: return empty list instead of crashing
            return []
    
    def get_by_id_and_tenant(
        self,
        ticket_id: int,
        tenant_id: int
    ) -> Optional[Ticket]:
        """Get ticket by ID and tenant"""
        return self.db.query(Ticket).filter(
            and_(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()
    
    def delete_by_source(
        self,
        tenant_id: int,
        sources: List[str]
    ) -> int:
        """Delete tickets by source (for cleanup)"""
        deleted = self.db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.source.in_(sources)
        ).delete()
        self.db.commit()
        return deleted


