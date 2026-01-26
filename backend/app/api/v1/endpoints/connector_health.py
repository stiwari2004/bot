"""
Connector Health API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.connector_health_service import ConnectorHealthService
from app.api.v1.endpoints.super_admin_auth import get_current_super_admin
from app.models.super_admin import SuperAdmin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/connector-health")
async def get_connector_health(
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get connector health summary"""
    try:
        service = ConnectorHealthService(db, tenant_id=tenant_id)
        health = service.get_connector_health_summary()
        return health
    except Exception as e:
        logger.error(f"Error fetching connector health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch connector health: {str(e)}")


@router.get("/connector-health/monitoring")
async def get_monitoring_connector_health(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get monitoring connector health status"""
    try:
        service = ConnectorHealthService(db)
        health = service.get_monitoring_connector_health()
        return health
    except Exception as e:
        logger.error(f"Error fetching monitoring connector health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch monitoring connector health: {str(e)}")


@router.get("/connector-health/ticketing")
async def get_ticketing_connector_health(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get ticketing connector health status"""
    try:
        service = ConnectorHealthService(db)
        health = service.get_ticketing_connector_health()
        return health
    except Exception as e:
        logger.error(f"Error fetching ticketing connector health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch ticketing connector health: {str(e)}")
