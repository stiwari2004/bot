"""
Super Admin export endpoints — CSV and PDF exports for dashboard data
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.super_admin import SuperAdmin
from app.services.super_admin_auth import get_current_super_admin
from app.services.dashboard.super_admin_dashboard_service import SuperAdminDashboardService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/dashboard/export/overview")
async def export_overview(
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Export dashboard overview as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        overview = service.get_overview()
        export_metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": current_admin.email,
            "timeframe": "current_month",
            "format": format,
        }

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

            title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=18,
                                         textColor=colors.HexColor("#1f2937"), spaceAfter=30)
            elements.append(Paragraph("Platform Overview Report", title_style))
            elements.append(Spacer(1, 0.2 * inch))

            summary = overview.get("summary", {})
            summary_data = [
                ["Metric", "Value"],
                ["Total Tenants", summary.get("total_tenants", 0)],
                ["Active Tenants", summary.get("active_tenants", 0)],
                ["Total Users", summary.get("total_users", 0)],
                ["Active Users", summary.get("active_users", 0)],
                ["Total Nodes", summary.get("total_nodes", 0)],
            ]
            _table_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ])
            t = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            t.setStyle(_table_style)
            elements.append(t)
            elements.append(Spacer(1, 0.3 * inch))

            revenue = overview.get("revenue", {})
            revenue_data = [
                ["Metric", "Value"],
                ["Total Revenue", f"${revenue.get('total_revenue', 0):,.2f}"],
                ["Fixed Revenue", f"${revenue.get('fixed_revenue', 0):,.2f}"],
                ["Node Overage", f"${revenue.get('node_overage_revenue', 0):,.2f}"],
                ["LLM Overage", f"${revenue.get('llm_overage_revenue', 0):,.2f}"],
            ]
            rev_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ])
            rt = Table(revenue_data, colWidths=[3 * inch, 2 * inch])
            rt.setStyle(rev_style)
            elements.append(rt)
            elements.append(Spacer(1, 0.3 * inch))

            footer_style = ParagraphStyle("CustomFooter", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            doc.build(elements)
            buffer.seek(0)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            return Response(content=buffer.getvalue(), media_type="application/pdf",
                            headers={"Content-Disposition": f"attachment; filename=overview_export_{ts}.pdf"})
        else:
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["# Platform Overview Export"])
            writer.writerow(["# Generated At", export_metadata["generated_at"]])
            writer.writerow(["# Generated By", export_metadata["generated_by"]])
            writer.writerow(["# Timeframe", export_metadata["timeframe"]])
            writer.writerow([])
            writer.writerow(["Section", "Metric", "Value"])
            for key, value in overview.get("summary", {}).items():
                writer.writerow(["Summary", key, value])
            for key, value in overview.get("revenue", {}).items():
                writer.writerow(["Revenue", key, value])
            for key, value in overview.get("usage", {}).items():
                writer.writerow(["Usage", key, value])
            output.seek(0)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                     headers={"Content-Disposition": f"attachment; filename=overview_export_{ts}.csv"})
    except Exception as e:
        logger.error(f"Error exporting overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export overview: {str(e)}")


@router.get("/dashboard/export/tenants")
async def export_tenants_csv(
    plan: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Export tenants list as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        result = service.get_tenants_list(skip=0, limit=10000, plan_filter=plan, status_filter=status)

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
            title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=18,
                                         textColor=colors.HexColor("#1f2937"), spaceAfter=30)
            elements.append(Paragraph("Tenants Export Report", title_style))
            elements.append(Spacer(1, 0.2 * inch))

            summary_data = [["Metric", "Value"], ["Total Tenants", result.get("total", 0)]]
            if plan:
                summary_data.append(["Filter: Plan", plan])
            if status:
                summary_data.append(["Filter: Status", status])
            tbl = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ]))
            elements.append(tbl)
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("Tenants List", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))

            tenants_data = [["ID", "Name", "Email", "Plan", "Status", "Nodes", "Revenue"]]
            for t in result.get("tenants", [])[:100]:
                tenants_data.append([
                    str(t.get("id", "")), t.get("name", "")[:30], (t.get("contact_email") or "")[:30],
                    t.get("plan_name", ""), "Active" if t.get("is_active") else "Inactive",
                    f"{t.get('nodes_used', 0)}/{t.get('nodes_limit', 0)}", f"${t.get('revenue', 0):,.2f}",
                ])
            rows_per_page = 25
            for i in range(0, len(tenants_data), rows_per_page):
                if i > 0:
                    elements.append(PageBreak())
                page_data = [tenants_data[0]] + tenants_data[i + 1:i + rows_per_page + 1]
                pt = Table(page_data, colWidths=[0.5*inch, 1.2*inch, 1.2*inch, 0.8*inch, 0.6*inch, 0.8*inch, 0.8*inch])
                pt.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ]))
                elements.append(pt)
            elements.append(Spacer(1, 0.3 * inch))
            footer_style = ParagraphStyle("CustomFooter", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            if len(result.get("tenants", [])) > 100:
                elements.append(Paragraph(f"Note: Showing first 100 of {result.get('total', 0)} tenants", footer_style))
            doc.build(elements)
            buffer.seek(0)
            return Response(content=buffer.getvalue(), media_type="application/pdf",
                            headers={"Content-Disposition": f"attachment; filename=tenants_export_{datetime.now().strftime('%Y%m%d')}.pdf"})
        else:
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "id", "name", "subdomain_slug", "contact_email", "is_active",
                "plan_name", "nodes_used", "nodes_limit", "llm_tokens", "revenue", "created_at",
            ])
            writer.writeheader()
            for t in result["tenants"]:
                writer.writerow({
                    "id": t["id"], "name": t["name"],
                    "subdomain_slug": t.get("subdomain_slug") or "", "contact_email": t.get("contact_email") or "",
                    "is_active": t["is_active"], "plan_name": t["plan_name"],
                    "nodes_used": t["nodes_used"], "nodes_limit": t["nodes_limit"],
                    "llm_tokens": t["llm_tokens"], "revenue": t["revenue"],
                    "created_at": t.get("created_at") or "",
                })
            output.seek(0)
            return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                     headers={"Content-Disposition": f"attachment; filename=tenants_export_{datetime.now().strftime('%Y%m%d')}.csv"})
    except Exception as e:
        logger.error(f"Error exporting tenants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export tenants: {str(e)}")


@router.get("/dashboard/export/revenue")
async def export_revenue_csv(
    months: int = Query(12, ge=1, le=24),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Export revenue analytics as CSV or PDF"""
    try:
        service = SuperAdminDashboardService(db)
        revenue_data = service.get_revenue_analytics(months=months)

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
            title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=18,
                                         textColor=colors.HexColor("#1f2937"), spaceAfter=30)
            elements.append(Paragraph("Revenue Analytics Report", title_style))
            elements.append(Spacer(1, 0.2 * inch))

            summary_data = [
                ["Metric", "Value"],
                ["Total Revenue", f"${revenue_data.get('total_revenue', 0):,.2f}"],
                ["Fixed Revenue", f"${revenue_data.get('fixed_revenue', 0):,.2f}"],
                ["Node Overage Revenue", f"${revenue_data.get('node_overage_revenue', 0):,.2f}"],
                ["LLM Overage Revenue", f"${revenue_data.get('llm_overage_revenue', 0):,.2f}"],
            ]
            if revenue_data.get("estimated_margin_percent"):
                summary_data.append(["Estimated Margin", f"{revenue_data['estimated_margin_percent']:.1f}%"])
            tbl = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ]))
            elements.append(tbl)
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("Monthly Breakdown", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))

            monthly_data = [["Month", "Revenue", "Period Start", "Period End"]]
            for m in revenue_data.get("revenue_by_month", []):
                monthly_data.append([m.get("month", ""), f"${m.get('revenue', 0):,.2f}",
                                     m.get("period_start", ""), m.get("period_end", "")])
            mt = Table(monthly_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            mt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]))
            elements.append(mt)
            elements.append(Spacer(1, 0.3 * inch))
            footer_style = ParagraphStyle("CustomFooter", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", footer_style))
            doc.build(elements)
            buffer.seek(0)
            return Response(content=buffer.getvalue(), media_type="application/pdf",
                            headers={"Content-Disposition": f"attachment; filename=revenue_export_{datetime.now().strftime('%Y%m%d')}.pdf"})
        else:
            from fastapi.responses import StreamingResponse
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=["month", "revenue", "period_start", "period_end"])
            writer.writeheader()
            for m in revenue_data.get("revenue_by_month", []):
                writer.writerow(m)
            output.seek(0)
            return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                                     headers={"Content-Disposition": f"attachment; filename=revenue_export_{datetime.now().strftime('%Y%m%d')}.csv"})
    except Exception as e:
        logger.error(f"Error exporting revenue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export revenue: {str(e)}")
