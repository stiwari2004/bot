"""
Alert Aggregator for dashboard alerts and notifications
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.tenant_subscription import TenantSubscription
from app.models.license_plan import LicensePlan
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AlertAggregator:
    """Aggregate alerts and notifications for dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get platform alerts and notifications"""
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Check for expiring trials
        expiring_soon = now + timedelta(days=7)
        expiring_count = self.db.query(TenantSubscription).join(
            LicensePlan, TenantSubscription.license_plan_id == LicensePlan.id
        ).filter(
            LicensePlan.plan_key == "trial",
            TenantSubscription.status == "active",
            TenantSubscription.expires_at.isnot(None),
            TenantSubscription.expires_at <= expiring_soon
        ).count()
        
        if expiring_count > 0:
            alerts.append({
                "type": "warning",
                "severity": "medium",
                "title": f"{expiring_count} trials expiring in 7 days",
                "message": "Some trial subscriptions are expiring soon",
                "action_required": True
            })
        
        # Check for tenants exceeding limits
        subscriptions_exceeding = self.db.query(TenantSubscription).filter(
            TenantSubscription.status == "active",
            or_(
                TenantSubscription.current_nodes > TenantSubscription.max_nodes,
                TenantSubscription.current_seats > TenantSubscription.max_seats
            )
        ).count()
        
        if subscriptions_exceeding > 0:
            alerts.append({
                "type": "warning",
                "severity": "high",
                "title": f"{subscriptions_exceeding} tenants exceeding limits",
                "message": "Some tenants have exceeded their subscription limits",
                "action_required": True
            })
        
        # Send email notifications for critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical" or a.get("severity") == "high"]
        if critical_alerts:
            self._send_critical_alert_emails(critical_alerts)
        
        return alerts
    
    def _send_critical_alert_emails(self, alerts: List[Dict[str, Any]]) -> None:
        """Send email notifications to super admins for critical alerts"""
        try:
            from app.services.email_service import get_email_service
            from app.models.super_admin import SuperAdmin
            
            email_service = get_email_service()
            
            # Get all active super admins
            super_admins = self.db.query(SuperAdmin).filter(SuperAdmin.is_active == True).all()
            
            if not super_admins:
                logger.warning("No active super admins found for critical alert notifications")
                return
            
            # Build email content
            critical_count = len([a for a in alerts if a.get("severity") == "critical"])
            high_count = len([a for a in alerts if a.get("severity") == "high"])
            
            subject = f"🚨 Critical Platform Alert{'s' if len(alerts) > 1 else ''} - {critical_count + high_count} Issue{'s' if len(alerts) > 1 else ''} Detected"
            
            alerts_html = ""
            for alert in alerts:
                severity_color = "red" if alert.get("severity") == "critical" else "orange"
                alerts_html += f"""
                <div style="margin: 15px 0; padding: 15px; border-left: 4px solid {severity_color}; background-color: #f9f9f9;">
                    <h3 style="margin: 0 0 10px 0; color: {severity_color};">
                        {alert.get("title", "Alert")}
                    </h3>
                    <p style="margin: 0; color: #333;">
                        {alert.get("message", "")}
                    </p>
                    {f'<p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">Tenant ID: {alert.get("tenant_id", "N/A")}</p>' if alert.get("tenant_id") else ""}
                </div>
                """
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #dc2626; color: white; padding: 20px; border-radius: 4px 4px 0 0; }}
                    .content {{ background-color: white; padding: 20px; border: 1px solid #ddd; border-top: none; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #666; text-align: center; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">🚨 Critical Platform Alert</h2>
                    </div>
                    <div class="content">
                        <p>Dear Super Administrator,</p>
                        <p>The following critical alert{'s have' if len(alerts) > 1 else ' has'} been detected on the platform:</p>
                        {alerts_html}
                        <p style="margin-top: 30px;">
                            <a href="{settings.FRONTEND_BASE_URL}/super-admin" class="button">View Dashboard</a>
                        </p>
                    </div>
                    <div class="footer">
                        <p>This is an automated alert notification from the Resolvify Platform.</p>
                        <p>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Critical Platform Alert
            
            Dear Super Administrator,
            
            The following critical alert(s) have been detected on the platform:
            
            {chr(10).join([f"- {a.get('title', 'Alert')}: {a.get('message', '')}" for a in alerts])}
            
            Please log in to the dashboard to review and take action:
            {settings.FRONTEND_BASE_URL}/super-admin
            
            This is an automated alert notification.
            """
            
            # Send to all super admins
            for admin in super_admins:
                email_service.send_email(
                    to_email=admin.email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body
                )
                logger.info(f"Sent critical alert email to super admin: {admin.email}")
                
        except Exception as e:
            logger.error(f"Failed to send critical alert emails: {e}", exc_info=True)
