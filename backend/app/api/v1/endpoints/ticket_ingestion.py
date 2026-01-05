"""
Alert and Ticket ingestion endpoints - Webhook receiver
Alerts come from monitoring tools, Tickets come from ticketing tools
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from enum import Enum
from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user, get_current_user_optional
from app.controllers.alert_controller import AlertController
from app.controllers.ticket_controller import TicketController

router = APIRouter()


# Validation enums
class TicketStatus(str, Enum):
    """Ticket status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ANALYZING = "analyzing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class WebhookSource(str, Enum):
    """Webhook source enumeration"""
    PROMETHEUS = "prometheus"
    DATADOG = "datadog"
    AZURE_MONITOR = "azure_monitor"
    SPLUNK = "splunk"
    PAGERDUTY = "pagerduty"
    SERVICENOW = "servicenow"
    JIRA = "jira"
    SOLARWINDS = "solarwinds"
    CUSTOM = "custom"


@router.post("/webhook/{source}")
async def receive_webhook(
    source: str = Path(..., min_length=1, max_length=50),
    payload: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Receive webhook from monitoring tools - Creates ALERTS, not tickets
    
    IMPORTANT: This creates an ALERT in the alerts table, NOT a ticket.
    Tickets come from ticketing tools (ServiceNow/ManageEngine) via polling.
    Alerts are used for validation and matching with tickets.
    
    Sources: prometheus, datadog, azure_monitor, splunk, pagerduty, servicenow, jira, solarwinds, custom
    """
    # Validate source
    if source not in [s.value for s in WebhookSource]:
        raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {', '.join([s.value for s in WebhookSource])}")
    
    # Validate payload
    if payload is None:
        raise HTTPException(status_code=400, detail="Payload is required")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    if len(str(payload)) > 100000:  # Limit payload size
        raise HTTPException(status_code=413, detail="Payload too large (max 100KB)")
    
    # Use AlertController to create alerts (not tickets)
    controller = AlertController(db, tenant_id=1)  # Demo tenant
    return await controller.receive_webhook(source, payload)


@router.post("/demo/ticket")
async def create_demo_ticket(
    ticket_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Create a demo ticket for testing"""
    controller = TicketController(db, tenant_id=1)  # Demo tenant
    return await controller.create_demo_ticket(ticket_data)


@router.get("/demo/tickets")
async def list_tickets(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """List tickets for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        controller = TicketController(db, tenant_id=tenant_id)
        result = controller.list_tickets(status, limit)
        # Ensure result is a dict with 'tickets' key
        if not isinstance(result, dict):
            result = {"tickets": []}
        if "tickets" not in result:
            result = {"tickets": result if isinstance(result, list) else []}
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.exception(f"Error in list_tickets: {e}", exc_info=True)
        # Return empty result instead of crashing
        return {"tickets": []}


@router.delete("/demo/tickets/cleanup-demo")
async def cleanup_demo_tickets(
    db: Session = Depends(get_db)
):
    """Delete demo/test tickets (prometheus and custom sources)"""
    controller = TicketController(db, tenant_id=1)  # Demo tenant
    return controller.cleanup_demo_tickets(["prometheus", "custom"])


@router.get("/demo/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ticket details including matched runbooks for the authenticated user's tenant"""
    try:
        # Use authenticated user's tenant_id - authentication required
        tenant_id = current_user.tenant_id
        controller = TicketController(db, tenant_id=tenant_id)
        return await controller.get_ticket(ticket_id)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.exception(f"Error in get_ticket: {e}", exc_info=True)
        # Return error response
        raise HTTPException(status_code=500, detail=f"Failed to get ticket: {str(e)}")


@router.post("/demo/tickets/{ticket_id}/execute")
async def execute_ticket_runbook(
    ticket_id: int,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a runbook for a ticket - requires authentication"""
    runbook_id = request.get("runbook_id")
    if not runbook_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="runbook_id is required")
    
    # Use authenticated user's tenant_id - authentication required
    tenant_id = current_user.tenant_id
    controller = TicketController(db, tenant_id=tenant_id)
    return await controller.execute_ticket_runbook(ticket_id, runbook_id)


@router.get("/demo/tickets/{ticket_id}/debug")
async def debug_ticket_meta_data(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to inspect ticket meta_data and matched runbooks"""
    from app.models.ticket import Ticket
    from app.models.runbook import Runbook
    
    # Use authenticated user's tenant_id - authentication required
    tenant_id = current_user.tenant_id
    
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.tenant_id == tenant_id
    ).first()
    
    if not ticket:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    # Get all runbooks to check associations
    all_runbooks = db.query(Runbook).filter(Runbook.tenant_id == tenant_id).all()
    
    return {
        "ticket_id": ticket.id,
        "ticket_title": ticket.title,
        "meta_data": ticket.meta_data,
        "meta_data_type": type(ticket.meta_data).__name__,
        "matched_runbooks_in_meta": ticket.meta_data.get("matched_runbooks", []) if ticket.meta_data else [],
        "total_runbooks": len(all_runbooks),
        "approved_runbooks": [{"id": rb.id, "title": rb.title, "status": rb.status, "is_active": rb.is_active} 
                              for rb in all_runbooks if rb.status == "approved"]
    }

