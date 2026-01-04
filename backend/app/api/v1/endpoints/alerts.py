"""
Alert endpoints - List and manage alerts from monitoring tools
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.controllers.alert_controller import AlertController

router = APIRouter()


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

