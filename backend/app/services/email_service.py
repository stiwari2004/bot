"""
Email service for sending emails (password reset, notifications, etc.)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
import os

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "noreply@troubleshooting-ai.com")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send to {to_email}: {subject}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, "plain")
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            
            # Send email
            if self.smtp_host == "localhost" or not self.smtp_user:
                # Development mode - log instead of sending
                logger.info(f"Email (dev mode) to {to_email}: {subject}")
                logger.debug(f"Email body: {html_body[:200]}...")
                return True
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False
    
    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email
        
        Args:
            to_email: User email address
            reset_token: Password reset token
            user_name: User's full name (optional)
            
        Returns:
            True if email sent successfully
        """
        reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?token={reset_token}"
        
        subject = "Password Reset Request"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .button:hover {{ background-color: #0056b3; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>You have requested to reset your password. Click the button below to reset it:</p>
                <p><a href="{reset_url}" class="button">Reset Password</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p>This link will expire in 1 hour.</p>
                <p>If you did not request a password reset, please ignore this email.</p>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Password Reset Request
        
        Hello {user_name or 'User'},
        
        You have requested to reset your password. Use the following link to reset it:
        
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you did not request a password reset, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_body, text_body)
    
    def send_email_verification_email(
        self,
        to_email: str,
        verification_token: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send email verification email
        
        Args:
            to_email: User email address
            verification_token: Email verification token
            user_name: User's full name (optional)
            
        Returns:
            True if email sent successfully
        """
        verify_url = f"{settings.BACKEND_BASE_URL}/api/v1/auth/verify-email?token={verification_token}"
        
        subject = "Verify Your Email Address"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Verify Your Email Address</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>Please verify your email address by clicking the button below:</p>
                <p><a href="{verify_url}" class="button">Verify Email</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{verify_url}</p>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Verify Your Email Address
        
        Hello {user_name or 'User'},
        
        Please verify your email address by visiting:
        
        {verify_url}
        """
        
        return self.send_email(to_email, subject, html_body, text_body)


# Global instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

