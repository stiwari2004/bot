"""
Super Admin Dashboard Endpoints
Comprehensive dashboard for platform-wide metrics, revenue, usage, and management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.dashboard.super_admin_dashboard_service import SuperAdminDashboardService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Response Models
class DashboardOverviewResponse(BaseModel):
    """Response model for dashboard overview"""
    summary: dict
    revenue: dict
    usage: dict
    plan_distribution: dict
    alerts: List[dict]
    timestamp: str


class TenantListItem(BaseModel):
    """Tenant list item with usage data"""
    id: int
    name: str
    subdomain_slug: Optional[str]
    contact_email: Optional[str]
    is_active: bool
    plan_name: str
    plan_key: Optional[str]
    nodes_used: int
    nodes_limit: int
    llm_tokens: int
    revenue: float
    created_at: Optional[str]


class TenantsListResponse(BaseModel):
    """Response for tenants list"""
    tenants: List[TenantListItem]
    total: int
    skip: int
    limit: int


# Dashboard Overview
@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get comprehensive platform overview dashboard"""
    try:
        service = SuperAdminDashboardService(db)
        overview = service.get_overview()
        return DashboardOverviewResponse(**overview)
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard overview: {str(e)}")


# Tenants Management
@router.get("/dashboard/tenants", response_model=TenantsListResponse)
async def get_dashboard_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    plan: Optional[str] = Query(None, description="Filter by plan key (trial, starter, professional, enterprise)"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    search: Optional[str] = Query(None, description="Search by tenant name or email"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get paginated list of tenants with usage data"""
    try:
        service = SuperAdminDashboardService(db)
        result = service.get_tenants_list(
            skip=skip,
            limit=limit,
            plan_filter=plan,
            status_filter=status,
            search=search
        )
        return TenantsListResponse(**result)
    except Exception as e:
        logger.error(f"Error fetching tenants list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch tenants list: {str(e)}")


# Revenue Analytics
@router.get("/dashboard/revenue")
async def get_dashboard_revenue(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get revenue analytics and trends"""
    try:
        service = SuperAdminDashboardService(db)
        revenue_data = service.get_revenue_analytics(months=months)
        return revenue_data
    except Exception as e:
        logger.error(f"Error fetching revenue analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch revenue analytics: {str(e)}")


# Trial Analytics
@router.get("/dashboard/trials")
async def get_dashboard_trials(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get trial subscription analytics"""
    try:
        service = SuperAdminDashboardService(db)
        trial_data = service.get_trial_analytics()
        return trial_data
    except Exception as e:
        logger.error(f"Error fetching trial analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch trial analytics: {str(e)}")


# Export endpoints
@router.get("/dashboard/export/tenants")
async def export_tenants_csv(
    plan: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Export tenants list as CSV"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        from io import StringIO
        
        service = SuperAdminDashboardService(db)
        result = service.get_tenants_list(
            skip=0,
            limit=10000,  # Large limit for export
            plan_filter=plan,
            status_filter=status
        )
        
        # Create CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "name", "subdomain_slug", "contact_email", "is_active",
            "plan_name", "nodes_used", "nodes_limit", "llm_tokens", "revenue", "created_at"
        ])
        writer.writeheader()
        
        for tenant in result["tenants"]:
            writer.writerow({
                "id": tenant["id"],
                "name": tenant["name"],
                "subdomain_slug": tenant.get("subdomain_slug") or "",
                "contact_email": tenant.get("contact_email") or "",
                "is_active": tenant["is_active"],
                "plan_name": tenant["plan_name"],
                "nodes_used": tenant["nodes_used"],
                "nodes_limit": tenant["nodes_limit"],
                "llm_tokens": tenant["llm_tokens"],
                "revenue": tenant["revenue"],
                "created_at": tenant.get("created_at") or ""
            })
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=tenants_export_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting tenants CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export tenants: {str(e)}")


@router.get("/dashboard/export/revenue")
async def export_revenue_csv(
    months: int = Query(12, ge=1, le=24),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Export revenue analytics as CSV"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        from io import StringIO
        
        service = SuperAdminDashboardService(db)
        revenue_data = service.get_revenue_analytics(months=months)
        
        # Create CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["month", "revenue", "period_start", "period_end"])
        writer.writeheader()
        
        for month_data in revenue_data["revenue_by_month"]:
            writer.writerow(month_data)
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=revenue_export_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting revenue CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export revenue: {str(e)}")
