"""
Report Email Service for sending scheduled reports via email
"""
from datetime import datetime
from typing import Dict, Any
from app.models.scheduled_report import ScheduledReport
from app.services.email_service import get_email_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportEmailService:
    """Service for sending report emails"""
    
    @staticmethod
    def send_report_email(report: ScheduledReport, report_data: Dict[str, Any]) -> None:
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
