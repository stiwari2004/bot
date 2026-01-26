"""
Reporting API endpoints for dynamic reports and scheduled reports
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.core.database import get_db
from app.models.super_admin import SuperAdmin
from app.models.scheduled_report import ScheduledReport, ReportFrequency, ReportFormat, ReportType
from app.services.super_admin_auth import get_current_super_admin
from app.services.reporting.report_service import ReportService
from app.services.reporting.scheduled_report_service import ScheduledReportService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Request/Response Models
class CustomReportRequest(BaseModel):
    """Request model for generating custom reports"""
    report_type: str  # overview, tenants, revenue, usage, custom
    format: str  # pdf, csv, excel
    filters: Optional[Dict[str, Any]] = None


class ScheduledReportCreate(BaseModel):
    """Request model for creating scheduled reports"""
    name: str
    description: Optional[str] = None
    report_type: str  # overview, tenants, revenue, usage, custom
    format: str  # pdf, csv, excel
    frequency: str  # daily, weekly, monthly, custom
    schedule_config: Dict[str, Any]
    recipients: List[EmailStr]
    filters: Optional[Dict[str, Any]] = None


class ScheduledReportUpdate(BaseModel):
    """Request model for updating scheduled reports"""
    name: Optional[str] = None
    description: Optional[str] = None
    report_type: Optional[str] = None
    format: Optional[str] = None
    frequency: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    recipients: Optional[List[EmailStr]] = None
    filters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ScheduledReportResponse(BaseModel):
    """Response model for scheduled reports"""
    id: int
    name: str
    description: Optional[str]
    report_type: str
    format: str
    frequency: str
    schedule_config: Dict[str, Any]
    recipients: List[str]
    filters: Dict[str, Any]
    is_active: bool
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    created_by_id: int
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


# Custom Report Generation
@router.post("/reports/generate")
async def generate_custom_report(
    request: CustomReportRequest,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Generate a custom report with filters"""
    try:
        service = ReportService(db)
        report_data = service.generate_custom_report(
            report_type=request.report_type,
            format=request.format,
            filters=request.filters or {}
        )
        return report_data
    except Exception as e:
        logger.error(f"Error generating custom report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# Scheduled Reports CRUD
@router.post("/reports/scheduled", response_model=ScheduledReportResponse)
async def create_scheduled_report(
    request: ScheduledReportCreate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Create a new scheduled report"""
    try:
        service = ScheduledReportService(db)
        
        # Validate enums
        try:
            report_type = ReportType(request.report_type)
            format = ReportFormat(request.format)
            frequency = ReportFrequency(request.frequency)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
        
        scheduled_report = service.create_scheduled_report(
            name=request.name,
            description=request.description,
            report_type=report_type,
            format=format,
            frequency=frequency,
            schedule_config=request.schedule_config,
            recipients=[str(email) for email in request.recipients],
            filters=request.filters,
            created_by_id=current_admin.id
        )
        
        return ScheduledReportResponse(
            id=scheduled_report.id,
            name=scheduled_report.name,
            description=scheduled_report.description,
            report_type=scheduled_report.report_type.value,
            format=scheduled_report.format.value,
            frequency=scheduled_report.frequency.value,
            schedule_config=scheduled_report.schedule_config,
            recipients=scheduled_report.recipients,
            filters=scheduled_report.filters,
            is_active=scheduled_report.is_active,
            last_run_at=scheduled_report.last_run_at.isoformat() if scheduled_report.last_run_at else None,
            next_run_at=scheduled_report.next_run_at.isoformat() if scheduled_report.next_run_at else None,
            created_by_id=scheduled_report.created_by_id,
            created_at=scheduled_report.created_at.isoformat(),
            updated_at=scheduled_report.updated_at.isoformat() if scheduled_report.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scheduled report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create scheduled report: {str(e)}")


@router.get("/reports/scheduled", response_model=List[ScheduledReportResponse])
async def list_scheduled_reports(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """List all scheduled reports (for current admin)"""
    try:
        service = ScheduledReportService(db)
        reports = service.get_scheduled_reports(
            created_by_id=current_admin.id,
            is_active=is_active
        )
        
        return [
            ScheduledReportResponse(
                id=report.id,
                name=report.name,
                description=report.description,
                report_type=report.report_type.value,
                format=report.format.value,
                frequency=report.frequency.value,
                schedule_config=report.schedule_config,
                recipients=report.recipients,
                filters=report.filters,
                is_active=report.is_active,
                last_run_at=report.last_run_at.isoformat() if report.last_run_at else None,
                next_run_at=report.next_run_at.isoformat() if report.next_run_at else None,
                created_by_id=report.created_by_id,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat() if report.updated_at else None
            )
            for report in reports
        ]
    except Exception as e:
        logger.error(f"Error listing scheduled reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list scheduled reports: {str(e)}")


@router.get("/reports/scheduled/{report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get a single scheduled report"""
    try:
        service = ScheduledReportService(db)
        report = service.get_scheduled_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        # Check ownership
        if report.created_by_id != current_admin.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this report")
        
        return ScheduledReportResponse(
            id=report.id,
            name=report.name,
            description=report.description,
            report_type=report.report_type.value,
            format=report.format.value,
            frequency=report.frequency.value,
            schedule_config=report.schedule_config,
            recipients=report.recipients,
            filters=report.filters,
            is_active=report.is_active,
            last_run_at=report.last_run_at.isoformat() if report.last_run_at else None,
            next_run_at=report.next_run_at.isoformat() if report.next_run_at else None,
            created_by_id=report.created_by_id,
            created_at=report.created_at.isoformat(),
            updated_at=report.updated_at.isoformat() if report.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scheduled report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scheduled report: {str(e)}")


@router.put("/reports/scheduled/{report_id}", response_model=ScheduledReportResponse)
async def update_scheduled_report(
    report_id: int,
    request: ScheduledReportUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update a scheduled report"""
    try:
        service = ScheduledReportService(db)
        report = service.get_scheduled_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        # Check ownership
        if report.created_by_id != current_admin.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this report")
        
        # Prepare update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.report_type is not None:
            update_data["report_type"] = ReportType(request.report_type)
        if request.format is not None:
            update_data["format"] = ReportFormat(request.format)
        if request.frequency is not None:
            update_data["frequency"] = ReportFrequency(request.frequency)
        if request.schedule_config is not None:
            update_data["schedule_config"] = request.schedule_config
        if request.recipients is not None:
            update_data["recipients"] = [str(email) for email in request.recipients]
        if request.filters is not None:
            update_data["filters"] = request.filters
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        updated_report = service.update_scheduled_report(report_id, **update_data)
        
        return ScheduledReportResponse(
            id=updated_report.id,
            name=updated_report.name,
            description=updated_report.description,
            report_type=updated_report.report_type.value,
            format=updated_report.format.value,
            frequency=updated_report.frequency.value,
            schedule_config=updated_report.schedule_config,
            recipients=updated_report.recipients,
            filters=updated_report.filters,
            is_active=updated_report.is_active,
            last_run_at=updated_report.last_run_at.isoformat() if updated_report.last_run_at else None,
            next_run_at=updated_report.next_run_at.isoformat() if updated_report.next_run_at else None,
            created_by_id=updated_report.created_by_id,
            created_at=updated_report.created_at.isoformat(),
            updated_at=updated_report.updated_at.isoformat() if updated_report.updated_at else None
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating scheduled report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update scheduled report: {str(e)}")


@router.delete("/reports/scheduled/{report_id}")
async def delete_scheduled_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Delete a scheduled report"""
    try:
        service = ScheduledReportService(db)
        report = service.get_scheduled_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        # Check ownership
        if report.created_by_id != current_admin.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this report")
        
        success = service.delete_scheduled_report(report_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete scheduled report")
        
        return {"message": "Scheduled report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete scheduled report: {str(e)}")


@router.post("/reports/scheduled/{report_id}/execute")
async def execute_scheduled_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Manually execute a scheduled report"""
    try:
        service = ScheduledReportService(db)
        report = service.get_scheduled_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Scheduled report not found")
        
        # Check ownership
        if report.created_by_id != current_admin.id:
            raise HTTPException(status_code=403, detail="Not authorized to execute this report")
        
        success = service.execute_scheduled_report(report_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to execute scheduled report")
        
        return {"message": "Scheduled report executed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing scheduled report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute scheduled report: {str(e)}")
