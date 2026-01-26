"""
Scheduled Report Service for managing automated reports
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

from app.models.scheduled_report import ScheduledReport, ReportFrequency, ReportFormat, ReportType
from app.services.reporting.report_service import ReportService
from app.services.email_service import get_email_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScheduledReportService:
    """Service for managing scheduled reports"""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_service = ReportService(db)
    
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
        next_run_at = self._calculate_next_run_time(frequency, schedule_config)
        
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
            report.next_run_at = self._calculate_next_run_time(
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
            
            # Export the report (this would generate PDF/CSV/Excel)
            # For now, we'll just log it - actual export would be handled by the export endpoints
            logger.info(f"Generated report for scheduled report {report_id}: {report.name}")
            
            # Send email to recipients
            self._send_report_email(report, report_data)
            
            # Update last run time and calculate next run time
            report.last_run_at = datetime.utcnow()
            report.next_run_at = self._calculate_next_run_time(
                report.frequency,
                report.schedule_config
            )
            
            self.db.commit()
            
            logger.info(f"Executed scheduled report {report_id} and sent to {len(report.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error executing scheduled report {report_id}: {e}", exc_info=True)
            return False
    
    def _calculate_next_run_time(
        self,
        frequency: ReportFrequency,
        schedule_config: Dict[str, Any]
    ) -> datetime:
        """Calculate the next run time based on frequency and schedule config"""
        now = datetime.utcnow()
        timezone = pytz.timezone(schedule_config.get("timezone", "UTC"))
        now_tz = now.replace(tzinfo=pytz.UTC).astimezone(timezone)
        
        # Get scheduled time
        time_str = schedule_config.get("time", "09:00")
        hour, minute = map(int, time_str.split(":"))
        
        if frequency == ReportFrequency.DAILY:
            # Run daily at specified time
            next_run = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now_tz:
                next_run += timedelta(days=1)
        
        elif frequency == ReportFrequency.WEEKLY:
            # Run weekly on specified day of week (0=Monday, 6=Sunday)
            day_of_week = schedule_config.get("day_of_week", 0)
            days_until_target = (day_of_week - now_tz.weekday()) % 7
            if days_until_target == 0 and now_tz.hour >= hour:
                days_until_target = 7
            next_run = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_until_target)
        
        elif frequency == ReportFrequency.MONTHLY:
            # Run monthly on specified day of month
            day_of_month = schedule_config.get("day_of_month", 1)
            next_run = now_tz.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now_tz:
                next_run += relativedelta(months=1)
        
        else:  # CUSTOM
            # For custom, use next_run_at from config or default to tomorrow
            if "next_run_at" in schedule_config:
                next_run = datetime.fromisoformat(schedule_config["next_run_at"])
                if next_run.tzinfo is None:
                    next_run = timezone.localize(next_run)
            else:
                next_run = now_tz + timedelta(days=1)
        
        # Convert back to UTC
        return next_run.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def _send_report_email(self, report: ScheduledReport, report_data: Dict[str, Any]) -> None:
        """Send the generated report via email"""
        email_service = get_email_service()
        
        # Generate report file (this would call the export endpoints)
        # For now, we'll create a simple email notification
        subject = f"Scheduled Report: {report.name}"
        
        html_body = f"""
        <html>
        <body>
            <h2>Scheduled Report: {report.name}</h2>
            <p>{report.description or 'No description provided.'}</p>
            <p><strong>Report Type:</strong> {report.report_type.value}</p>
            <p><strong>Generated At:</strong> {report_data.get('generated_at', datetime.utcnow().isoformat())}</p>
            <p>Please log in to the dashboard to view and download the full report.</p>
        </body>
        </html>
        """
        
        text_body = f"""
        Scheduled Report: {report.name}
        
        {report.description or 'No description provided.'}
        
        Report Type: {report.report_type.value}
        Generated At: {report_data.get('generated_at', datetime.utcnow().isoformat())}
        
        Please log in to the dashboard to view and download the full report.
        """
        
        # Send to all recipients
        for recipient in report.recipients:
            try:
                email_service.send_email(
                    to_email=recipient,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body
                )
                logger.info(f"Sent scheduled report email to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}", exc_info=True)
