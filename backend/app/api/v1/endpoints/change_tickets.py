"""
Change Ticket API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.models.change_ticket import ChangeTicket
from app.models.ticket import Ticket
from app.services.auth import get_current_user
from app.models.user import User
from app.services.change_window_service import get_change_window_service
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Schemas
class ChangeTicketResponse(BaseModel):
    id: int
    tenant_id: int
    external_id: str
    source: str
    title: str
    description: Optional[str]
    change_type: Optional[str]
    status: str
    start_time: datetime
    end_time: datetime
    affected_services: Optional[List[str]]
    affected_environments: Optional[List[str]]
    suppression_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SuppressedTicketResponse(BaseModel):
    id: int
    title: str
    severity: str
    environment: str
    service: Optional[str]
    suppressed_at: datetime
    suppression_reason: Optional[str]
    change_ticket: Optional[ChangeTicketResponse]
    
    class Config:
        from_attributes = True


@router.get("/change-tickets", response_model=List[ChangeTicketResponse])
async def list_change_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Show only active change windows"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List change tickets for current tenant"""
    try:
        query = db.query(ChangeTicket).filter(
            ChangeTicket.tenant_id == current_user.tenant_id
        )
        
        if status:
            query = query.filter(ChangeTicket.status == status)
        
        if active_only:
            now = datetime.now(timezone.utc)
            query = query.filter(
                ChangeTicket.status.in_(['scheduled', 'in_progress']),
                ChangeTicket.suppression_enabled == True,
                ChangeTicket.start_time <= now,
                ChangeTicket.end_time >= now
            )
        
        change_tickets = query.order_by(ChangeTicket.start_time.desc()).all()
        
        return change_tickets
        
    except Exception as e:
        logger.error(f"Error listing change tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list change tickets")


@router.get("/change-tickets/{change_ticket_id}", response_model=ChangeTicketResponse)
async def get_change_ticket(
    change_ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get change ticket details"""
    try:
        change_ticket = db.query(ChangeTicket).filter(
            ChangeTicket.id == change_ticket_id,
            ChangeTicket.tenant_id == current_user.tenant_id
        ).first()
        
        if not change_ticket:
            raise HTTPException(status_code=404, detail="Change ticket not found")
        
        return change_ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting change ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get change ticket")


@router.get("/change-tickets/suppressed-tickets", response_model=List[SuppressedTicketResponse])
async def list_suppressed_tickets(
    change_ticket_id: Optional[int] = Query(None, description="Filter by change ticket ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List tickets suppressed by change windows"""
    try:
        query = db.query(Ticket).filter(
            Ticket.tenant_id == current_user.tenant_id,
            Ticket.suppressed == True
        )
        
        if change_ticket_id:
            query = query.filter(Ticket.suppressed_by_change_ticket_id == change_ticket_id)
        
        suppressed_tickets = query.order_by(Ticket.suppressed_at.desc()).all()
        
        result = []
        for ticket in suppressed_tickets:
            change_ticket_data = None
            if ticket.suppressed_by_change_ticket_id:
                change_ticket = db.query(ChangeTicket).filter(
                    ChangeTicket.id == ticket.suppressed_by_change_ticket_id
                ).first()
                if change_ticket:
                    change_ticket_data = ChangeTicketResponse.from_orm(change_ticket)
            
            result.append(SuppressedTicketResponse(
                id=ticket.id,
                title=ticket.title,
                severity=ticket.severity,
                environment=ticket.environment,
                service=ticket.service,
                suppressed_at=ticket.suppressed_at,
                suppression_reason=ticket.suppression_reason,
                change_ticket=change_ticket_data
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing suppressed tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list suppressed tickets")


@router.post("/change-tickets/{change_ticket_id}/unsuppress-tickets")
async def unsuppress_tickets_for_change(
    change_ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually unsuppress all tickets for a change window"""
    try:
        change_ticket = db.query(ChangeTicket).filter(
            ChangeTicket.id == change_ticket_id,
            ChangeTicket.tenant_id == current_user.tenant_id
        ).first()
        
        if not change_ticket:
            raise HTTPException(status_code=404, detail="Change ticket not found")
        
        # Get all suppressed tickets for this change
        suppressed_tickets = db.query(Ticket).filter(
            Ticket.tenant_id == current_user.tenant_id,
            Ticket.suppressed == True,
            Ticket.suppressed_by_change_ticket_id == change_ticket_id
        ).all()
        
        change_window_service = get_change_window_service()
        unsuppressed_count = 0
        
        for ticket in suppressed_tickets:
            change_window_service.unsuppress_ticket(db, ticket)
            unsuppressed_count += 1
        
        logger.info(f"Manually unsuppressed {unsuppressed_count} tickets for change {change_ticket_id}")
        
        return {
            "message": f"Unsuppressed {unsuppressed_count} tickets",
            "unsuppressed_count": unsuppressed_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsuppressing tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unsuppress tickets")

