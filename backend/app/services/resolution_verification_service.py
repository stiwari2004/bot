"""
Resolution Verification Service - Verify if ticket issue is actually resolved
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.ticket_status_service import get_ticket_status_service
from app.services.threshold_service import get_threshold_service
from app.services.ticketing_integration_service import get_ticketing_integration_service
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

logger = get_logger(__name__)


class ResolutionVerificationService:
    """Service for verifying if ticket issues are resolved after runbook execution"""
    
    def __init__(self):
        self.ticket_status_service = get_ticket_status_service()
        self.threshold_service = get_threshold_service()
        self.ticketing_integration_service = get_ticketing_integration_service()
    
    async def verify_resolution(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify if the ticket issue is resolved after execution
        
        Args:
            db: Database session
            session_id: Execution session ID
            ticket_id: Ticket ID (optional, will fetch from session if not provided)
            
        Returns:
            {
                "resolved": bool,
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "verification_method": str
            }
        """
        try:
            # Get execution session
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise ValueError(f"Execution session {session_id} not found")
            
            # Get ticket ID from session if not provided
            if not ticket_id:
                ticket_id = session.ticket_id
            
            if not ticket_id:
                logger.warning(f"No ticket_id for session {session_id}, skipping resolution verification")
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "No ticket associated with execution",
                    "verification_method": "none"
                }
            
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found")
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "Ticket not found",
                    "verification_method": "none"
                }
            
            # Check execution status
            if session.status != "completed":
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": f"Execution not completed (status: {session.status})",
                    "verification_method": "execution_status"
                }
            
            # Method 1: Check if all steps succeeded
            all_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id
            ).all()
            
            if not all_steps:
                return {
                    "resolved": False,
                    "confidence": 0.0,
                    "reasoning": "No execution steps found",
                    "verification_method": "step_analysis"
                }
            
            # Check step success rate
            successful_steps = [s for s in all_steps if s.completed and s.success]
            failed_steps = [s for s in all_steps if s.completed and s.success is False]
            
            success_rate = len(successful_steps) / len(all_steps) if all_steps else 0.0
            
            # Method 2: Check postchecks (if they exist) and compare to prechecks
            postchecks = [s for s in all_steps if s.step_type == "postcheck"]
            prechecks = [s for s in all_steps if s.step_type == "precheck"]
            
            # Enhanced verification: Compare precheck vs postcheck metrics
            if prechecks and postchecks:
                comparison_result = self._compare_precheck_postcheck(
                    db=db,
                    ticket_id=ticket_id,
                    prechecks=prechecks,
                    postchecks=postchecks
                )
                
                if comparison_result:
                    # Use comparison result if available
                    resolved = comparison_result.get("resolved", False)
                    confidence = comparison_result.get("confidence", 0.5)
                    reasoning = comparison_result.get("reasoning", "Compared precheck vs postcheck metrics")
                    verification_method = "precheck_postcheck_comparison"
                else:
                    # Fallback to step success analysis
                    postcheck_success = all(s.success for s in postchecks if s.completed)
                    resolved = success_rate == 1.0 and postcheck_success
                    confidence = 0.7 if resolved else 0.5
                    reasoning = f"Postchecks passed: {postcheck_success}, but could not compare metrics"
                    verification_method = "step_analysis"
            else:
                # No postchecks or prechecks - use step success rate
                postcheck_success = all(s.success for s in postchecks if s.completed) if postchecks else True
                
                # High confidence if all steps succeeded and postchecks passed
                if success_rate == 1.0 and postcheck_success:
                    resolved = True
                    confidence = 0.9
                    reasoning = "All execution steps completed successfully"
                    verification_method = "step_analysis"
                
                # Medium confidence if most steps succeeded
                elif success_rate >= 0.8:
                    resolved = True
                    confidence = 0.7
                    reasoning = f"Most steps succeeded ({len(successful_steps)}/{len(all_steps)})"
                    verification_method = "step_analysis"
                
                # Low confidence if mixed results
                elif success_rate >= 0.5:
                    resolved = False  # Uncertain, need manual verification
                    confidence = 0.5
                    reasoning = f"Mixed results ({len(successful_steps)}/{len(all_steps)} steps succeeded)"
                    verification_method = "step_analysis"
                
                # Low confidence if most steps failed
                else:
                    resolved = False
                    confidence = 0.9
                    reasoning = f"Most steps failed ({len(failed_steps)}/{len(all_steps)} steps failed)"
                    verification_method = "step_analysis"
            
            # Update ticket status based on verification
            if resolved:
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, ticket_id, "completed", issue_resolved=True
                )
                # Update external ticket
                ticket.resolution_verified_at = datetime.now(timezone.utc)
                db.commit()
                await self.ticketing_integration_service.resolve_ticket(
                    db=db,
                    ticket=ticket,
                    resolution_notes=reasoning
                )
            else:
                # Keep as in_progress for manual review if uncertain
                if confidence < 0.7:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, ticket_id, "completed", issue_resolved=None
                    )
                    # Mark for manual review in external system
                    ticket.escalation_reason = f"Uncertain resolution: {reasoning}"
                    db.commit()
                    await self.ticketing_integration_service.mark_for_manual_review(
                        db=db,
                        ticket=ticket,
                        reason=f"Uncertain resolution: {reasoning}"
                    )
                else:
                    self.ticket_status_service.update_ticket_on_execution_complete(
                        db, ticket_id, "completed", issue_resolved=False
                    )
                    # Escalate in external system
                    ticket.escalation_reason = f"Issue not resolved: {reasoning}"
                    db.commit()
                    await self.ticketing_integration_service.escalate_ticket(
                        db=db,
                        ticket=ticket,
                        escalation_reason=f"Issue not resolved: {reasoning}"
                    )
            
            logger.info(
                f"Resolution verification for ticket {ticket_id}: "
                f"resolved={resolved}, confidence={confidence:.2f}, method={verification_method}"
            )
            
            return {
                "resolved": resolved,
                "confidence": confidence,
                "reasoning": reasoning,
                "verification_method": verification_method,
                "success_rate": success_rate,
                "total_steps": len(all_steps),
                "successful_steps": len(successful_steps),
                "failed_steps": len(failed_steps)
            }
            
        except Exception as e:
            logger.error(f"Error verifying resolution for session {session_id}: {e}")
            return {
                "resolved": False,
                "confidence": 0.0,
                "reasoning": f"Verification failed: {str(e)}",
                "verification_method": "error"
            }
    
    async def verify_resolution_with_llm(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify resolution using LLM analysis of execution output
        This is a more sophisticated method that analyzes step outputs
        """
        # For POC, we'll use the step-based verification
        # In production, this could analyze step outputs with LLM
        result = await self.verify_resolution(db, session_id, ticket_id)
        
        # TODO: Enhance with LLM analysis of step outputs
        # This would involve:
        # 1. Collecting all step outputs
        # 2. Analyzing them with LLM to determine if issue is resolved
        # 3. Returning higher confidence result
        
        return result
    
    def _compare_precheck_postcheck(
        self,
        db: Session,
        ticket_id: int,
        prechecks: List[ExecutionStep],
        postchecks: List[ExecutionStep]
    ) -> Optional[Dict[str, Any]]:
        """
        Compare precheck and postcheck outputs to determine if issue is resolved
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            prechecks: List of precheck steps
            postchecks: List of postcheck steps
            
        Returns:
            Comparison result or None if comparison not possible
        """
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return None
            
            # Extract metrics from precheck outputs
            precheck_metrics = {}
            for precheck in prechecks:
                if precheck.completed and precheck.success and precheck.output:
                    metrics = self._extract_metrics_from_output(
                        precheck.output,
                        precheck.command or ""
                    )
                    precheck_metrics.update(metrics)
            
            # Extract metrics from postcheck outputs
            postcheck_metrics = {}
            for postcheck in postchecks:
                if postcheck.completed and postcheck.success and postcheck.output:
                    metrics = self._extract_metrics_from_output(
                        postcheck.output,
                        postcheck.command or ""
                    )
                    postcheck_metrics.update(metrics)
            
            if not precheck_metrics or not postcheck_metrics:
                return None
            
            # Compare metrics
            improvements = []
            regressions = []
            unchanged = []
            
            for metric_name in set(precheck_metrics.keys()) & set(postcheck_metrics.keys()):
                pre_value = precheck_metrics[metric_name]
                post_value = postcheck_metrics[metric_name]
                
                # Get thresholds
                thresholds = self.threshold_service.get_thresholds(
                    metric=metric_name,
                    environment=ticket.environment,
                    service=ticket.service,
                    tenant_id=ticket.tenant_id
                )
                warning_threshold = thresholds.get("warning", 80.0)
                
                # Check if metric improved (moved from above threshold to below)
                if pre_value >= warning_threshold and post_value < warning_threshold:
                    improvements.append(
                        f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (resolved)"
                    )
                elif pre_value < warning_threshold and post_value >= warning_threshold:
                    regressions.append(
                        f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (worsened)"
                    )
                elif abs(pre_value - post_value) < 5.0:  # Less than 5% change
                    unchanged.append(
                        f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (unchanged)"
                    )
                elif post_value < pre_value:
                    # Improved but still above threshold
                    improvements.append(
                        f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (improved)"
                    )
                else:
                    regressions.append(
                        f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (worsened)"
                    )
            
            # Determine resolution status
            if improvements and not regressions:
                resolved = True
                confidence = 0.9
                reasoning = f"Issue resolved: {', '.join(improvements)}"
            elif improvements and regressions:
                resolved = False
                confidence = 0.6
                reasoning = f"Mixed results: {', '.join(improvements)} but {', '.join(regressions)}"
            elif regressions:
                resolved = False
                confidence = 0.8
                reasoning = f"Issue not resolved: {', '.join(regressions)}"
            elif unchanged:
                resolved = False
                confidence = 0.7
                reasoning = f"No significant change: {', '.join(unchanged)}"
            else:
                resolved = False
                confidence = 0.5
                reasoning = "Could not determine resolution status from metrics"
            
            return {
                "resolved": resolved,
                "confidence": confidence,
                "reasoning": reasoning,
                "precheck_metrics": precheck_metrics,
                "postcheck_metrics": postcheck_metrics
            }
            
        except Exception as e:
            logger.error(f"Error comparing precheck/postcheck: {e}", exc_info=True)
            return None
    
    def _extract_metrics_from_output(self, output: str, command: str) -> Dict[str, float]:
        """
        Extract metric values from command output
        
        Args:
            output: Command output text
            command: Command that was executed
            
        Returns:
            Dictionary of metric_name -> value
        """
        metrics = {}
        output_lower = output.lower()
        command_lower = command.lower()
        
        # CPU metrics
        if any(keyword in command_lower for keyword in ["cpu", "processor", "processor time"]):
            cpu_value = self._extract_percentage_value(output)
            if cpu_value is not None:
                metrics["cpu"] = cpu_value
        
        # Memory metrics
        if any(keyword in command_lower for keyword in ["memory", "ram", "mem"]):
            mem_value = self._extract_percentage_value(output)
            if mem_value is not None:
                metrics["memory"] = mem_value
        
        # Disk metrics
        if any(keyword in command_lower for keyword in ["disk", "storage", "space", "usage"]):
            disk_value = self._extract_percentage_value(output)
            if disk_value is not None:
                metrics["disk"] = disk_value
        
        # Network metrics
        if any(keyword in command_lower for keyword in ["network", "bandwidth", "traffic"]):
            network_value = self._extract_percentage_value(output)
            if network_value is not None:
                metrics["network"] = network_value
        
        return metrics
    
    def _extract_percentage_value(self, output: str) -> Optional[float]:
        """
        Extract percentage value from output
        
        Args:
            output: Command output
            
        Returns:
            Percentage value (0-100) or None
        """
        # Try various patterns
        patterns = [
            r'(\d+\.?\d*)\s*%',  # "95.5%" or "95 %"
            r'(\d+\.?\d*)\s*percent',  # "95.5 percent"
            r':\s*(\d+\.?\d*)',  # ": 95.5"
            r'=\s*(\d+\.?\d*)',  # "= 95.5"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[-1])  # Take last match
                    if 0 <= value <= 100:
                        return value
                    elif value > 100:
                        # Might be in 0-1 format, convert
                        return value / 100.0 * 100 if value <= 1 else None
                except (ValueError, IndexError):
                    continue
        
        return None


# Global instance
_resolution_verification_service: Optional[ResolutionVerificationService] = None


def get_resolution_verification_service() -> ResolutionVerificationService:
    """Get or create resolution verification service instance"""
    global _resolution_verification_service
    if _resolution_verification_service is None:
        _resolution_verification_service = ResolutionVerificationService()
    return _resolution_verification_service




