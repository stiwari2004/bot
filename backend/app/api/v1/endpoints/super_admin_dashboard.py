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


# Dashboard Preferences
@router.get("/dashboard/preferences")
async def get_dashboard_preferences(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Get dashboard preferences for the current super admin"""
    try:
        # For now, return default preferences
        # In the future, this could be stored in a database table
        return {
            "widgets": {
                "summary_cards": {"enabled": True, "order": 0},
                "revenue": {"enabled": True, "order": 1},
                "usage_metrics": {"enabled": True, "order": 2},
                "alerts": {"enabled": True, "order": 3},
                "plan_distribution": {"enabled": True, "order": 4},
            },
            "refresh_interval": 30000,  # 30 seconds in milliseconds
            "auto_refresh": True
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch preferences: {str(e)}")


@router.put("/dashboard/preferences")
async def update_dashboard_preferences(
    preferences: dict,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Update dashboard preferences for the current super admin"""
    try:
        # For now, just validate and return success
        # In the future, this should be stored in a database table
        # Validate preferences structure
        if "widgets" not in preferences:
            raise HTTPException(status_code=400, detail="Missing 'widgets' in preferences")
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "preferences": preferences
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


# Export endpoints
@router.get("/dashboard/export/overview")
async def export_overview(
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Export dashboard overview as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        overview = service.get_overview()
        
        if format == "pdf":
            from fastapi.responses import Response
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
            )
            elements.append(Paragraph("Platform Overview Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary section
            summary = overview.get("summary", {})
            summary_data = [
                ["Metric", "Value"],
                ["Total Tenants", summary.get("total_tenants", 0)],
                ["Active Tenants", summary.get("active_tenants", 0)],
                ["Total Users", summary.get("total_users", 0)],
                ["Active Users", summary.get("active_users", 0)],
                ["Total Nodes", summary.get("total_nodes", 0)],
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Revenue section
            revenue = overview.get("revenue", {})
            revenue_data = [
                ["Metric", "Value"],
                ["Total Revenue", f"${revenue.get('total_revenue', 0):,.2f}"],
                ["Fixed Revenue", f"${revenue.get('fixed_revenue', 0):,.2f}"],
                ["Node Overage", f"${revenue.get('node_overage_revenue', 0):,.2f}"],
                ["LLM Overage", f"${revenue.get('llm_overage_revenue', 0):,.2f}"],
            ]
            
            revenue_table = Table(revenue_data, colWidths=[3*inch, 2*inch])
            revenue_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            elements.append(revenue_table)
            
            # Footer
            elements.append(Spacer(1, 0.3*inch))
            footer_style = ParagraphStyle(
                'CustomFooter',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
            )
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            
            doc.build(elements)
            buffer.seek(0)
            
            return Response(
                content=buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=overview_export_{datetime.now().strftime('%Y%m%d')}.pdf"}
            )
        else:
            # CSV export
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Section", "Metric", "Value"])
            
            # Summary
            summary = overview.get("summary", {})
            for key, value in summary.items():
                writer.writerow(["Summary", key, value])
            
            # Revenue
            revenue = overview.get("revenue", {})
            for key, value in revenue.items():
                writer.writerow(["Revenue", key, value])
            
            # Usage
            usage = overview.get("usage", {})
            for key, value in usage.items():
                writer.writerow(["Usage", key, value])
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=overview_export_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
    except Exception as e:
        logger.error(f"Error exporting overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export overview: {str(e)}")


@router.get("/dashboard/export/tenants")
async def export_tenants_csv(
    plan: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Export tenants list as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        result = service.get_tenants_list(
            skip=0,
            limit=10000,  # Large limit for export
            plan_filter=plan,
            status_filter=status
        )
        
        if format == "pdf":
            from fastapi.responses import Response
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
            )
            elements.append(Paragraph("Tenants Export Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary
            summary_data = [
                ["Metric", "Value"],
                ["Total Tenants", result.get("total", 0)],
            ]
            if plan:
                summary_data.append(["Filter: Plan", plan])
            if status:
                summary_data.append(["Filter: Status", status])
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Tenants table
            elements.append(Paragraph("Tenants List", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            
            tenants_data = [["ID", "Name", "Email", "Plan", "Status", "Nodes", "Revenue"]]
            for tenant in result.get("tenants", [])[:100]:  # Limit to 100 for PDF
                tenants_data.append([
                    str(tenant.get("id", "")),
                    tenant.get("name", "")[:30],  # Truncate long names
                    (tenant.get("contact_email") or "")[:30],
                    tenant.get("plan_name", ""),
                    "Active" if tenant.get("is_active") else "Inactive",
                    f"{tenant.get('nodes_used', 0)}/{tenant.get('nodes_limit', 0)}",
                    f"${tenant.get('revenue', 0):,.2f}"
                ])
            
            # Split into multiple pages if needed
            rows_per_page = 25
            for i in range(0, len(tenants_data), rows_per_page):
                if i > 0:
                    elements.append(PageBreak())
                
                page_data = [tenants_data[0]] + tenants_data[i+1:i+rows_per_page+1]
                tenants_table = Table(page_data, colWidths=[0.5*inch, 1.2*inch, 1.2*inch, 0.8*inch, 0.6*inch, 0.8*inch, 0.8*inch])
                tenants_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                ]))
                elements.append(tenants_table)
            
            # Footer
            elements.append(Spacer(1, 0.3*inch))
            footer_style = ParagraphStyle(
                'CustomFooter',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
            )
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            if len(result.get("tenants", [])) > 100:
                elements.append(Paragraph(f"Note: Showing first 100 of {result.get('total', 0)} tenants", footer_style))
            
            doc.build(elements)
            buffer.seek(0)
            
            return Response(
                content=buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=tenants_export_{datetime.now().strftime('%Y%m%d')}.pdf"}
            )
        else:
            # CSV export
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            
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
        logger.error(f"Error exporting tenants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export tenants: {str(e)}")


@router.get("/dashboard/export/revenue")
async def export_revenue_csv(
    months: int = Query(12, ge=1, le=24),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """Export revenue analytics as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        revenue_data = service.get_revenue_analytics(months=months)
        
        if format == "pdf":
            from fastapi.responses import Response
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
            )
            elements.append(Paragraph("Revenue Analytics Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary
            summary_data = [
                ["Metric", "Value"],
                ["Total Revenue", f"${revenue_data.get('total_revenue', 0):,.2f}"],
                ["Fixed Revenue", f"${revenue_data.get('fixed_revenue', 0):,.2f}"],
                ["Node Overage Revenue", f"${revenue_data.get('node_overage_revenue', 0):,.2f}"],
                ["LLM Overage Revenue", f"${revenue_data.get('llm_overage_revenue', 0):,.2f}"],
            ]
            if revenue_data.get('estimated_margin_percent'):
                summary_data.append(["Estimated Margin", f"{revenue_data['estimated_margin_percent']:.1f}%"])
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Monthly breakdown
            elements.append(Paragraph("Monthly Breakdown", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            
            monthly_data = [["Month", "Revenue", "Period Start", "Period End"]]
            for month_data in revenue_data.get("revenue_by_month", []):
                monthly_data.append([
                    month_data.get("month", ""),
                    f"${month_data.get('revenue', 0):,.2f}",
                    month_data.get("period_start", ""),
                    month_data.get("period_end", "")
                ])
            
            monthly_table = Table(monthly_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            monthly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            elements.append(monthly_table)
            
            # Footer
            elements.append(Spacer(1, 0.3*inch))
            footer_style = ParagraphStyle(
                'CustomFooter',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
            )
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            
            doc.build(elements)
            buffer.seek(0)
            
            return Response(
                content=buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=revenue_export_{datetime.now().strftime('%Y%m%d')}.pdf"}
            )
        else:
            # CSV export
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=["month", "revenue", "period_start", "period_end"])
            writer.writeheader()
            
            for month_data in revenue_data.get("revenue_by_month", []):
                writer.writerow(month_data)
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=revenue_export_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
    except Exception as e:
        logger.error(f"Error exporting revenue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export revenue: {str(e)}")
