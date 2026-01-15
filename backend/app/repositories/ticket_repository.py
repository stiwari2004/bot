"""
Repository for ticket data access
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
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
        """Get all tickets for a tenant, optionally filtered by status with eager loading"""
        try:
            query = self.db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
            
            # Eager load tenant relationship to prevent N+1 queries
            query = query.options(joinedload(Ticket.tenant))
            
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
        """Get ticket by ID and tenant with eager loading"""
        query = self.db.query(Ticket).filter(
            and_(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        )
        # Eager load tenant relationship
        query = query.options(joinedload(Ticket.tenant))
        return query.first()
    
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
    
    def create_ticket(
        self,
        tenant_id: int,
        source: str,
        external_id: Optional[str],
        title: str,
        description: Optional[str],
        severity: str,
        environment: str,
        service: Optional[str],
        status: str,
        raw_payload: Optional[Dict[str, Any]],
        meta_data: Optional[Dict[str, Any]],
        received_at: Optional[datetime] = None
    ) -> Ticket:
        """Create a new ticket with all fields"""
        from datetime import datetime, timezone
        ticket = Ticket(
            tenant_id=tenant_id,
            source=source,
            external_id=external_id,
            title=title,
            description=description,
            severity=severity,
            environment=environment,
            service=service,
            status=status,
            raw_payload=raw_payload,
            meta_data=meta_data,
            received_at=received_at or datetime.now(timezone.utc)
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket
    
    def update_ticket_metadata(
        self,
        ticket_id: int,
        tenant_id: int,
        meta_data: Dict[str, Any]
    ) -> Optional[Ticket]:
        """Update ticket metadata"""
        ticket = self.get_by_id_and_tenant(ticket_id, tenant_id)
        if ticket:
            if not ticket.meta_data:
                ticket.meta_data = {}
            ticket.meta_data.update(meta_data)
            self.db.commit()
            self.db.refresh(ticket)
        return ticket
    
    def update_ticket(
        self,
        ticket_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[Ticket]:
        """Update ticket fields"""
        ticket = self.get_by_id_and_tenant(ticket_id, tenant_id)
        if ticket:
            for key, value in kwargs.items():
                setattr(ticket, key, value)
            self.db.commit()
            self.db.refresh(ticket)
        return ticket


