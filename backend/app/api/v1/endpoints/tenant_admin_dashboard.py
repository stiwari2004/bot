"""
Tenant Admin Dashboard Endpoints
Dashboard for tenant-level metrics, usage, and management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.dashboard.tenant_admin_dashboard_service import TenantAdminDashboardService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Response Models
class TenantDashboardOverviewResponse(BaseModel):
    """Response model for tenant dashboard overview"""
    summary: dict
    usage: dict
    billing: dict
    alerts: list
    timestamp: str


# Dashboard Overview
@router.get("/dashboard/overview", response_model=TenantDashboardOverviewResponse)
async def get_tenant_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive tenant overview dashboard"""
    try:
        # Verify user has tenant admin role or is tenant admin
        if current_user.role not in ["tenant_admin", "msp_admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        service = TenantAdminDashboardService(db, current_user.tenant_id)
        overview = service.get_overview()
        return TenantDashboardOverviewResponse(**overview)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching tenant dashboard overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard overview: {str(e)}")


# Export endpoints
@router.get("/dashboard/export/overview")
async def export_tenant_overview(
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export tenant dashboard overview as CSV or PDF"""
    try:
        if current_user.role not in ["tenant_admin", "msp_admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        service = TenantAdminDashboardService(db, current_user.tenant_id)
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
            tenant_name = overview.get("summary", {}).get("tenant_name", "Tenant")
            elements.append(Paragraph(f"{tenant_name} - Dashboard Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary section
            summary = overview.get("summary", {})
            summary_data = [
                ["Metric", "Value"],
                ["Total Users", summary.get("total_users", 0)],
                ["Active Users", summary.get("active_users", 0)],
                ["Total Nodes", summary.get("total_nodes", 0)],
                ["Plan", summary.get("plan_name", "N/A")],
                ["Nodes Used", f"{summary.get('nodes_used', 0)}/{summary.get('nodes_limit', 0)}"],
                ["Seats Used", f"{summary.get('seats_used', 0)}/{summary.get('seats_limit', 0)}"],
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
            
            # Usage section
            usage = overview.get("usage", {})
            usage_data = [
                ["Metric", "Value"],
                ["Executions", usage.get("total_executions", 0)],
                ["Tickets", usage.get("total_tickets", 0)],
                ["LLM Tokens", f"{usage.get('total_llm_tokens', 0):,}"],
                ["API Calls", f"{usage.get('total_api_calls', 0):,}"],
            ]
            
            usage_table = Table(usage_data, colWidths=[3*inch, 2*inch])
            usage_table.setStyle(TableStyle([
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
            elements.append(usage_table)
            
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
                headers={"Content-Disposition": f"attachment; filename=tenant_dashboard_{datetime.now().strftime('%Y%m%d')}.pdf"}
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
            
            # Usage
            usage = overview.get("usage", {})
            for key, value in usage.items():
                writer.writerow(["Usage", key, value])
            
            # Billing
            billing = overview.get("billing", {})
            for key, value in billing.items():
                writer.writerow(["Billing", key, value])
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=tenant_dashboard_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting tenant overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export overview: {str(e)}")
