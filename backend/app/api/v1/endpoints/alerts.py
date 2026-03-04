"""
Alert endpoints - List and manage alerts from monitoring tools
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
from app.core.database import get_db
from app.controllers.alert_controller import AlertController
from app.models.monitoring_tool_connection import MonitoringToolConnection
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class WebhookSource(str, Enum):
    """Webhook source enumeration"""
    PROMETHEUS = "prometheus"
    DATADOG = "datadog"
    AZURE_MONITOR = "azure_monitor"
    SPLUNK = "splunk"
    PAGERDUTY = "pagerduty"
    SOLARWINDS = "solarwinds"
    OP_MANAGER = "opmanager"
    CUSTOM = "custom"


class AlertUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("/alerts")
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (firing, resolved, acknowledged)"),
    source: Optional[str] = Query(None, description="Filter by source (prometheus, datadog, azure_monitor, splunk, solarwinds)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    db: Session = Depends(get_db)
):
    """
    List alerts from monitoring tools
    
    Alerts are separate from tickets:
    - Alerts come from monitoring tools (Prometheus, Datadog, Azure Monitor, Splunk, SolarWinds)
    - Tickets come from ticketing tools (ServiceNow, ManageEngine, Zoho)
    - Alerts can be matched with tickets for validation
    """
    controller = AlertController(db, tenant_id=1)  # Demo tenant
    return controller.list_alerts(status=status, source=source, limit=limit)


@router.get("/alerts/{alert_id}")
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get alert details by ID"""
    controller = AlertController(db, tenant_id=1)  # Demo tenant
    return controller.get_alert(alert_id)


@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: int,
    update: AlertUpdateRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update alert status (resolve, acknowledge, etc.)
    
    Valid statuses:
    - firing: Alert is active
    - resolved: Alert has been resolved
    - acknowledged: Alert has been acknowledged
    
    You can also add notes to track the update.
    """
    controller = AlertController(db, tenant_id=1)  # Demo tenant
    return await controller.update_alert(
        alert_id=alert_id,
        status=update.status,
        notes=update.notes
    )


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
    
    Sources: prometheus, datadog, azure_monitor, splunk, pagerduty, solarwinds, custom
    
    Tenant is determined by looking up the monitoring connection for this source.
    If multiple connections exist, uses the first active one.
    Falls back to tenant_id=1 (demo) if no connection found.
    
    This endpoint is also available at /api/v1/tickets/webhook/{source} for backward compatibility.
    """
    # Validate source
    if source not in [s.value for s in WebhookSource]:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join([s.value for s in WebhookSource])}"
        )
    
    # Validate payload
    if payload is None:
        raise HTTPException(status_code=400, detail="Payload is required")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    if len(str(payload)) > 100000:  # Limit payload size
        raise HTTPException(status_code=413, detail="Payload too large (max 100KB)")
    
    # Determine tenant_id from monitoring connection
    # Look for an active webhook connection for this source
    connection = db.query(MonitoringToolConnection).filter(
        MonitoringToolConnection.tool_name == source,
        MonitoringToolConnection.connection_type == "webhook",
        MonitoringToolConnection.is_active == True
    ).first()
    
    if connection:
        tenant_id = connection.tenant_id
        logger.info(f"Webhook received from {source}, using tenant_id={tenant_id} from connection {connection.id}")
    else:
        # Fallback to demo tenant if no connection found
        tenant_id = 1
        logger.warning(
            f"Webhook received from {source}, but no active webhook connection found. "
            f"Using demo tenant_id=1"
        )
    
    # Use AlertController to create alerts (not tickets)
    controller = AlertController(db, tenant_id=tenant_id)
    return await controller.receive_webhook(source, payload)

