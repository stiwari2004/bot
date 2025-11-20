"""
Ticket ingestion endpoints - Webhook receiver
POC version - simplified
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.core.database import get_db
from app.controllers.ticket_controller import TicketController

router = APIRouter()


@router.post("/webhook/{source}")
async def receive_webhook(
    source: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Receive webhook from monitoring tools
    
    Sources: prometheus, datadog, pagerduty, servicenow, jira, custom
    """
    controller = TicketController(db, tenant_id=1)  # Demo tenant
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
    status: str = None,
    limit: int = 50
):
    """List tickets (demo)"""
    try:
        controller = TicketController(db, tenant_id=1)  # Demo tenant
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
    db: Session = Depends(get_db)
):
    """Get ticket details including matched runbooks"""
    try:
        controller = TicketController(db, tenant_id=1)  # Demo tenant
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
    db: Session = Depends(get_db)
):
    """Execute a runbook for a ticket"""
    runbook_id = request.get("runbook_id")
    if not runbook_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="runbook_id is required")
    
    controller = TicketController(db, tenant_id=1)  # Demo tenant
    return await controller.execute_ticket_runbook(ticket_id, runbook_id)

