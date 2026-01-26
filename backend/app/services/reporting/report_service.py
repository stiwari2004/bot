"""
Report Service for dynamic report generation
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.services.dashboard.super_admin_dashboard_service import SuperAdminDashboardService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportService:
    """Service for generating dynamic reports"""
    
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_service = SuperAdminDashboardService(db)
    
    def generate_custom_report(
        self,
        report_type: str,
        format: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a custom report based on type and filters
        
        Args:
            report_type: Type of report (overview, tenants, revenue, usage, custom)
            format: Output format (pdf, csv, excel)
            filters: Optional filters to apply
            
        Returns:
            Report data dictionary
        """
        filters = filters or {}
        
        if report_type == "overview":
            return self._generate_overview_report(filters)
        elif report_type == "tenants":
            return self._generate_tenants_report(filters)
        elif report_type == "revenue":
            return self._generate_revenue_report(filters)
        elif report_type == "usage":
            return self._generate_usage_report(filters)
        elif report_type == "custom":
            return self._generate_custom_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def _generate_overview_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overview report with optional filters"""
        overview = self.dashboard_service.get_overview()
        
        # Apply date range filter if provided
        if "date_range" in filters:
            date_range = filters["date_range"]
            # Note: Current dashboard service doesn't support date ranges
            # This would require extending the service
            pass
        
        # Filter by tenant IDs if provided
        if "tenant_ids" in filters and filters["tenant_ids"]:
            # Filter alerts and other tenant-specific data
            tenant_ids = set(filters["tenant_ids"])
            if overview.get("alerts"):
                overview["alerts"] = [
                    alert for alert in overview["alerts"]
                    if alert.get("tenant_id") in tenant_ids or alert.get("tenant_id") is None
                ]
        
        return {
            "type": "overview",
            "data": overview,
            "filters_applied": filters,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_tenants_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tenants report with filters"""
        skip = filters.get("skip", 0)
        limit = filters.get("limit", 1000)
        plan_filter = filters.get("plan")
        status_filter = filters.get("status")
        search = filters.get("search")
        tenant_ids = filters.get("tenant_ids")
        
        result = self.dashboard_service.get_tenants_list(
            skip=skip,
            limit=limit,
            plan_filter=plan_filter,
            status_filter=status_filter,
            search=search
        )
        
        # Filter by specific tenant IDs if provided
        if tenant_ids:
            result["tenants"] = [
                tenant for tenant in result["tenants"]
                if tenant["id"] in tenant_ids
            ]
            result["total"] = len(result["tenants"])
        
        return {
            "type": "tenants",
            "data": result,
            "filters_applied": filters,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_revenue_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate revenue report with filters"""
        months = filters.get("months", 12)
        
        revenue_data = self.dashboard_service.get_revenue_analytics(months=months)
        
        # Apply date range filter if provided
        if "date_range" in filters:
            date_range = filters["date_range"]
            # Filter revenue data by date range
            # This would require extending the service to support date ranges
            pass
        
        return {
            "type": "revenue",
            "data": revenue_data,
            "filters_applied": filters,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_usage_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate usage metrics report"""
        overview = self.dashboard_service.get_overview()
        
        usage_data = {
            "total_executions": overview.get("usage", {}).get("total_executions", 0),
            "total_tickets": overview.get("usage", {}).get("total_tickets", 0),
            "total_llm_tokens": overview.get("usage", {}).get("total_llm_tokens", 0),
            "total_api_calls": overview.get("usage", {}).get("total_api_calls", 0),
        }
        
        # Apply tenant filter if provided
        if "tenant_ids" in filters and filters["tenant_ids"]:
            # This would require querying usage per tenant
            # For now, return overall usage
            pass
        
        return {
            "type": "usage",
            "data": usage_data,
            "filters_applied": filters,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_custom_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a custom report combining multiple data sources"""
        report_data = {}
        
        # Include overview if requested
        if filters.get("include_overview", True):
            report_data["overview"] = self._generate_overview_report(filters)
        
        # Include tenants if requested
        if filters.get("include_tenants", False):
            report_data["tenants"] = self._generate_tenants_report(filters)
        
        # Include revenue if requested
        if filters.get("include_revenue", False):
            report_data["revenue"] = self._generate_revenue_report(filters)
        
        # Include usage if requested
        if filters.get("include_usage", False):
            report_data["usage"] = self._generate_usage_report(filters)
        
        return {
            "type": "custom",
            "data": report_data,
            "filters_applied": filters,
            "generated_at": datetime.utcnow().isoformat()
        }
