"""
Ticket Step Tracker Service
Tracks execution steps in tickets for audit trail and external system sync
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.core.input_sanitizer import sanitize_for_logging
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionStep
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json

logger = get_logger(__name__)


class TicketStepTracker:
    """Service for tracking execution steps in tickets"""
    
    def __init__(self):
        self.ticketing_service = None
        # Lazy import to avoid circular dependencies
        try:
            from app.services.ticketing_integration_service import TicketingIntegrationService
            self.ticketing_service = TicketingIntegrationService()
        except ImportError:
            logger.warning("TicketingIntegrationService not available")
    
    def track_step_in_ticket(
        self,
        db: Session,
        ticket_id: int,
        step: ExecutionStep,
        connector_type: Optional[str] = None
    ) -> bool:
        """
        Track a completed step in the ticket's metadata
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            step: ExecutionStep object
            connector_type: Type of connector used (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from sqlalchemy.orm.attributes import flag_modified
            
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found for step tracking")
                return False
            
            # Get or initialize meta_data
            if ticket.meta_data:
                meta_data = dict(ticket.meta_data) if isinstance(ticket.meta_data, dict) else json.loads(ticket.meta_data) if isinstance(ticket.meta_data, str) else {}
            else:
                meta_data = {}
            
            # Initialize execution_steps array if it doesn't exist
            if "execution_steps" not in meta_data:
                meta_data["execution_steps"] = []
            
            # Create step summary (sanitized for storage)
            step_summary = {
                "step_number": step.step_number,
                "step_type": step.step_type or "main",
                "command": self._sanitize_command(step.command or ""),
                "status": "success" if step.success else "failed",
                "completed_at": step.completed_at.isoformat() if step.completed_at else datetime.now(timezone.utc).isoformat(),
                "duration_ms": None,  # Will be calculated if available
                "connector_type": connector_type,
                "has_output": bool(step.output),
                "has_error": bool(step.error),
                "error_preview": (step.error[:200] if step.error else None) if not step.success else None,
            }
            
            # Add output preview (first 500 chars, sanitized)
            if step.output:
                output_preview = step.output[:500]
                # Further sanitize output for storage
                output_preview = sanitize_for_logging(output_preview)
                step_summary["output_preview"] = output_preview
            
            # Check if this step already exists (update instead of duplicate)
            steps = meta_data["execution_steps"]
            existing_index = None
            for idx, existing_step in enumerate(steps):
                if existing_step.get("step_number") == step.step_number:
                    existing_index = idx
                    break
            
            if existing_index is not None:
                # Update existing step
                steps[existing_index] = step_summary
                logger.debug(f"Updated step {step.step_number} in ticket {ticket_id} metadata")
            else:
                # Add new step
                steps.append(step_summary)
                logger.debug(f"Added step {step.step_number} to ticket {ticket_id} metadata")
            
            # Keep only last 100 steps to prevent metadata bloat
            if len(steps) > 100:
                meta_data["execution_steps"] = steps[-100:]
                logger.info(f"Trimmed execution_steps in ticket {ticket_id} to last 100 steps")
            
            # Update ticket metadata
            ticket.meta_data = meta_data
            flag_modified(ticket, "meta_data")
            ticket.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Tracked step {step.step_number} in ticket {ticket_id} metadata")
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking step in ticket {ticket_id}: {e}", exc_info=True)
            db.rollback()
            return False
    
    async def add_step_comment_to_external_ticket(
        self,
        db: Session,
        ticket_id: int,
        step: ExecutionStep,
        connector_type: Optional[str] = None
    ) -> bool:
        """
        Add a comment to external ticketing system about the step execution
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            step: ExecutionStep object
            connector_type: Type of connector used (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.ticketing_service:
                logger.debug("TicketingIntegrationService not available, skipping external comment")
                return False
            
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket or not ticket.external_id:
                logger.debug(f"Ticket {ticket_id} has no external_id, skipping external comment")
                return False
            
            # Build comment text
            status_emoji = "✅" if step.success else "❌"
            status_text = "completed successfully" if step.success else "failed"
            
            comment_lines = [
                f"{status_emoji} Step {step.step_number} ({step.step_type or 'main'}) {status_text}",
                f"Command: {self._sanitize_command(step.command or 'N/A')[:200]}",
            ]
            
            if step.error and not step.success:
                # Include error preview for failed steps
                error_preview = step.error[:300]
                error_preview = sanitize_for_logging(error_preview)
                comment_lines.append(f"Error: {error_preview}")
            elif step.output and step.success:
                # Include brief output preview for successful steps
                output_preview = step.output[:200]
                output_preview = sanitize_for_logging(output_preview)
                # Only add if output is meaningful (not just whitespace)
                if output_preview.strip():
                    comment_lines.append(f"Output: {output_preview}")
            
            if connector_type:
                comment_lines.append(f"Connector: {connector_type}")
            
            if step.completed_at:
                comment_lines.append(f"Time: {step.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            comment_text = "\n".join(comment_lines)
            
            # Add comment to external ticket
            # Use a generic status update - most ticketing systems will add this as a comment
            success = await self.ticketing_service.add_ticket_comment(
                db=db,
                ticket=ticket,
                comment=comment_text
            )
            
            if success:
                logger.info(f"Added step {step.step_number} comment to external ticket {ticket.external_id}")
            else:
                logger.warning(f"Failed to add step {step.step_number} comment to external ticket {ticket.external_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding step comment to external ticket {ticket_id}: {e}", exc_info=True)
            return False
    
    def _sanitize_command(self, command: str) -> str:
        """
        Sanitize command for storage/display
        Removes or masks sensitive information
        """
        if not command:
            return ""
        
        # Use the existing sanitizer
        sanitized = sanitize_for_logging(command)
        
        # Additional sanitization: truncate very long commands
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "... [truncated]"
        
        return sanitized
    
    def get_ticket_step_summary(
        self,
        db: Session,
        ticket_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get summary of all steps executed for a ticket
        
        Returns:
            Dict with step summary statistics, or None if ticket not found
        """
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return None
            
            if not ticket.meta_data or "execution_steps" not in ticket.meta_data:
                return {
                    "total_steps": 0,
                    "successful_steps": 0,
                    "failed_steps": 0,
                    "steps": []
                }
            
            steps = ticket.meta_data.get("execution_steps", [])
            
            successful = sum(1 for s in steps if s.get("status") == "success")
            failed = sum(1 for s in steps if s.get("status") == "failed")
            
            return {
                "total_steps": len(steps),
                "successful_steps": successful,
                "failed_steps": failed,
                "steps": steps
            }
            
        except Exception as e:
            logger.error(f"Error getting ticket step summary for {ticket_id}: {e}", exc_info=True)
            return None


# Global instance
_ticket_step_tracker: Optional[TicketStepTracker] = None


def get_ticket_step_tracker() -> TicketStepTracker:
    """Get or create ticket step tracker instance"""
    global _ticket_step_tracker
    if _ticket_step_tracker is None:
        _ticket_step_tracker = TicketStepTracker()
    return _ticket_step_tracker

