"""
Scheduled Report Service for managing automated reports
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.scheduled_report import ScheduledReport, ReportFrequency, ReportFormat, ReportType
from app.services.reporting.report_service import ReportService
from app.services.reporting.schedule_calculator import ScheduleCalculator
from app.services.reporting.report_email_service import ReportEmailService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScheduledReportService:
    """Service for managing scheduled reports"""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_service = ReportService(db)
        self.schedule_calculator = ScheduleCalculator()
        self.email_service = ReportEmailService()
    
    def create_scheduled_report(
        self,
        name: str,
        description: Optional[str],
        report_type: ReportType,
        format: ReportFormat,
        frequency: ReportFrequency,
        schedule_config: Dict[str, Any],
        recipients: List[str],
        filters: Optional[Dict[str, Any]],
        created_by_id: int
    ) -> ScheduledReport:
        """Create a new scheduled report"""
        # Calculate next run time
        next_run_at = self.schedule_calculator.calculate_next_run_time(frequency, schedule_config)
        
        scheduled_report = ScheduledReport(
            name=name,
            description=description,
            report_type=report_type,
            format=format,
            frequency=frequency,
            schedule_config=schedule_config,
            recipients=recipients,
            filters=filters or {},
            is_active=True,
            next_run_at=next_run_at,
            created_by_id=created_by_id
        )
        
        self.db.add(scheduled_report)
        self.db.commit()
        self.db.refresh(scheduled_report)
        
        logger.info(f"Created scheduled report: {name} (ID: {scheduled_report.id})")
        return scheduled_report
    
    def update_scheduled_report(
        self,
        report_id: int,
        **kwargs
    ) -> Optional[ScheduledReport]:
        """Update a scheduled report"""
        report = self.db.query(ScheduledReport).filter(ScheduledReport.id == report_id).first()
        if not report:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        
        # Recalculate next run time if schedule changed
        if "frequency" in kwargs or "schedule_config" in kwargs:
            report.next_run_at = self.schedule_calculator.calculate_next_run_time(
                report.frequency,
                report.schedule_config
            )
        
        self.db.commit()
        self.db.refresh(report)
        
        logger.info(f"Updated scheduled report: {report_id}")
        return report
    
    def delete_scheduled_report(self, report_id: int) -> bool:
        """Delete a scheduled report"""
        report = self.db.query(ScheduledReport).filter(ScheduledReport.id == report_id).first()
        if not report:
            return False
        
        self.db.delete(report)
        self.db.commit()
        
        logger.info(f"Deleted scheduled report: {report_id}")
        return True
    
    def get_scheduled_reports(
        self,
        created_by_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[ScheduledReport]:
        """Get scheduled reports with optional filters"""
        query = self.db.query(ScheduledReport)
        
        if created_by_id is not None:
            query = query.filter(ScheduledReport.created_by_id == created_by_id)
        
        if is_active is not None:
            query = query.filter(ScheduledReport.is_active == is_active)
        
        return query.order_by(ScheduledReport.created_at.desc()).all()
    
    def get_scheduled_report(self, report_id: int) -> Optional[ScheduledReport]:
        """Get a single scheduled report"""
        return self.db.query(ScheduledReport).filter(ScheduledReport.id == report_id).first()
    
    def get_reports_due_for_execution(self) -> List[ScheduledReport]:
        """Get all active reports that are due for execution"""
        now = datetime.utcnow()
        return self.db.query(ScheduledReport).filter(
            and_(
                ScheduledReport.is_active == True,
                ScheduledReport.next_run_at <= now
            )
        ).all()
    
    def execute_scheduled_report(self, report_id: int) -> bool:
        """Execute a scheduled report and send it to recipients"""
        report = self.get_scheduled_report(report_id)
        if not report or not report.is_active:
            return False
        
        try:
            # Generate the report
            report_data = self.report_service.generate_custom_report(
                report_type=report.report_type.value,
                format=report.format.value,
                filters=report.filters
            )
            
            logger.info(f"Generated report for scheduled report {report_id}: {report.name}")
            
            # Send email to recipients
            self.email_service.send_report_email(report, report_data)
            
            # Update last run time and calculate next run time
            report.last_run_at = datetime.utcnow()
            report.next_run_at = self.schedule_calculator.calculate_next_run_time(
                report.frequency,
                report.schedule_config
            )
            
            self.db.commit()
            
            logger.info(f"Executed scheduled report {report_id} and sent to {len(report.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error executing scheduled report {report_id}: {e}", exc_info=True)
            return False
