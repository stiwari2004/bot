"""
Time Remaining Service
Checks if sufficient time remains for self-healing remediation
"""
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession
from app.models.ticket import Ticket

logger = get_logger(__name__)


class TimeRemainingService:
    """Service for checking if sufficient time remains for self-healing"""
    
    # Minimum time required for self-healing (15 minutes + 5 minute buffer)
    MIN_TIME_REQUIRED_MINUTES = 20
    
    def has_sufficient_time(
        self,
        db: Session,
        ticket: Ticket,
        current_session: Optional[ExecutionSession] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if sufficient time remains for self-healing
        
        Args:
            db: Database session
            ticket: Ticket being processed
            current_session: Current execution session (optional)
            
        Returns:
            (has_time, reason) - True if sufficient time, False with reason if not
        """
        try:
            # Get ticket SLA or default timeout
            # For now, use a default of 4 hours from ticket creation
            ticket_timeout_minutes = 240  # 4 hours default
            
            # Calculate time elapsed since ticket creation
            if ticket.received_at:
                elapsed = datetime.now(timezone.utc) - ticket.received_at
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
            
            # Calculate time remaining
            time_remaining_minutes = ticket_timeout_minutes - elapsed_minutes
            
            # Check if sufficient time remains
            if time_remaining_minutes >= self.MIN_TIME_REQUIRED_MINUTES:
                return (True, None)
            else:
                reason = (
                    f"Insufficient time remaining: {time_remaining_minutes:.1f} minutes "
                    f"(minimum {self.MIN_TIME_REQUIRED_MINUTES} minutes required)"
                )
                return (False, reason)
                
        except Exception as e:
            logger.error(f"Error checking time remaining: {e}", exc_info=True)
            # Conservative: assume no time if check fails
            return (False, f"Time check failed: {str(e)}")
    
    def get_time_remaining_minutes(
        self,
        ticket: Ticket
    ) -> float:
        """
        Get time remaining in minutes
        
        Args:
            ticket: Ticket to check
            
        Returns:
            Time remaining in minutes (0 if expired)
        """
        try:
            ticket_timeout_minutes = 240  # 4 hours default
            
            if ticket.received_at:
                elapsed = datetime.now(timezone.utc) - ticket.received_at
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
            
            time_remaining = ticket_timeout_minutes - elapsed_minutes
            return max(0.0, time_remaining)
            
        except Exception as e:
            logger.error(f"Error calculating time remaining: {e}", exc_info=True)
            return 0.0


# Global instance
_time_remaining_service: Optional[TimeRemainingService] = None


def get_time_remaining_service() -> TimeRemainingService:
    """Get or create time remaining service instance"""
    global _time_remaining_service
    if _time_remaining_service is None:
        _time_remaining_service = TimeRemainingService()
    return _time_remaining_service

