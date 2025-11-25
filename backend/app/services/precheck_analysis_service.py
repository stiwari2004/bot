"""
Precheck Analysis Service - Analyze precheck outputs to determine false positives
"""
import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.services.threshold_service import get_threshold_service

logger = get_logger(__name__)


class PrecheckAnalysisService:
    """Service for analyzing precheck outputs to determine if ticket is false positive"""
    
    def __init__(self):
        self.threshold_service = get_threshold_service()
    
    async def analyze_precheck_outputs(
        self,
        db: Session,
        ticket: Ticket,
        session: ExecutionSession,
        runbook: Optional[Runbook] = None
    ) -> Dict[str, Any]:
        """
        Analyze precheck step outputs to determine if ticket is false positive
        
        Args:
            db: Database session
            ticket: Ticket object
            session: Execution session
            runbook: Optional runbook object
            
        Returns:
            {
                "is_false_positive": bool,
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "analysis_status": str,  # "success", "failed", "ambiguous"
                "metrics": Dict[str, float]  # Extracted metrics
            }
        """
        try:
            logger.info(f"Starting precheck analysis for ticket {ticket.id}, session {session.id}")
            
            # Get all precheck steps
            precheck_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.step_type == "precheck"
            ).order_by(ExecutionStep.step_number).all()
            
            if not precheck_steps:
                logger.warning(f"No precheck steps found for session {session.id}")
                return {
                    "is_false_positive": False,
                    "confidence": 0.0,
                    "reasoning": "No precheck steps found",
                    "analysis_status": "failed",
                    "metrics": {}
                }
            
            logger.info(f"Found {len(precheck_steps)} precheck steps for session {session.id}")
            
            # Check if any precheck steps failed to execute
            failed_steps = [s for s in precheck_steps if not s.completed or s.success is False]
            if failed_steps:
                error_messages = [s.error or "Unknown error" for s in failed_steps if s.error]
                return {
                    "is_false_positive": False,
                    "confidence": 0.0,
                    "reasoning": f"Precheck execution failed: {', '.join(error_messages[:3])}",
                    "analysis_status": "failed",
                    "metrics": {}
                }
            
            # Collect all precheck outputs
            precheck_outputs = []
            for step in precheck_steps:
                if step.completed and step.success and step.output:
                    precheck_outputs.append({
                        "step_number": step.step_number,
                        "command": step.command,
                        "output": step.output,
                        "description": getattr(step, 'description', '')
                    })
            
            if not precheck_outputs:
                logger.warning(f"No precheck outputs available for session {session.id}")
                return {
                    "is_false_positive": False,
                    "confidence": 0.0,
                    "reasoning": "No precheck outputs available",
                    "analysis_status": "failed",
                    "metrics": {}
                }
            
            logger.info(f"Analyzing {len(precheck_outputs)} precheck outputs for ticket {ticket.id}")
            
            # Analyze outputs
            analysis_result = await self._analyze_outputs(
                ticket=ticket,
                precheck_outputs=precheck_outputs,
                runbook=runbook,
                db=db
            )
            
            logger.info(
                f"Precheck analysis complete for ticket {ticket.id}: "
                f"is_false_positive={analysis_result.get('is_false_positive')}, "
                f"confidence={analysis_result.get('confidence'):.2f}, "
                f"status={analysis_result.get('analysis_status')}"
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing precheck outputs: {e}", exc_info=True)
            return {
                "is_false_positive": False,
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}",
                "analysis_status": "failed",
                "metrics": {}
            }
    
    async def _analyze_outputs(
        self,
        ticket: Ticket,
        precheck_outputs: List[Dict[str, Any]],
        runbook: Optional[Runbook] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Analyze precheck outputs to determine false positive
        
        Args:
            ticket: Ticket object
            precheck_outputs: List of precheck output dictionaries
            runbook: Optional runbook object
            
        Returns:
            Analysis result dictionary
        """
        # Extract metrics from outputs
        extracted_metrics = {}
        ambiguous_outputs = []
        
        logger.info(f"Extracting metrics from {len(precheck_outputs)} precheck outputs")
        
        for precheck in precheck_outputs:
            output = precheck.get("output", "")
            command = precheck.get("command", "").lower()
            description = precheck.get("description", "").lower()
            step_number = precheck.get("step_number", 0)
            
            # Try to extract metrics
            metrics = self._extract_metrics_from_output(output, command, description)
            
            if metrics:
                logger.info(f"Extracted metrics from precheck step {step_number}: {metrics}")
                extracted_metrics.update(metrics)
            else:
                # Check if output is ambiguous
                if self._is_ambiguous_output(output):
                    logger.warning(f"Ambiguous output detected in precheck step {step_number}")
                    ambiguous_outputs.append(step_number)
                else:
                    logger.debug(f"No metrics extracted from precheck step {step_number}, but output is not ambiguous")
        
        # If we have ambiguous outputs, escalate
        if ambiguous_outputs:
            return {
                "is_false_positive": False,
                "confidence": 0.0,
                "reasoning": f"Ambiguous precheck outputs at steps: {ambiguous_outputs}",
                "analysis_status": "ambiguous",
                "metrics": extracted_metrics
            }
        
        # If no metrics extracted, try to analyze based on ticket description
        if not extracted_metrics:
            return {
                "is_false_positive": False,
                "confidence": 0.5,
                "reasoning": "Could not extract metrics from precheck outputs, proceeding with execution",
                "analysis_status": "success",
                "metrics": {}
            }
        
        # Compare metrics to ticket description and thresholds
        comparison_result = await self._compare_metrics_to_ticket(
            ticket=ticket,
            metrics=extracted_metrics,
            runbook=runbook,
            db=db
        )
        
        return {
            **comparison_result,
            "analysis_status": "success",
            "metrics": extracted_metrics
        }
    
    def _extract_metrics_from_output(
        self,
        output: str,
        command: str,
        description: str
    ) -> Dict[str, float]:
        """
        Extract metric values from command output
        
        Args:
            output: Command output text
            command: Command that was executed
            description: Step description
            
        Returns:
            Dictionary of metric_name -> value
        """
        metrics = {}
        output_lower = output.lower()
        
        # CPU metrics
        if any(keyword in command or keyword in description for keyword in ["cpu", "processor", "processor time"]):
            cpu_value = self._extract_percentage_value(output, ["cpu", "processor"])
            if cpu_value is not None:
                metrics["cpu"] = cpu_value
        
        # Memory metrics
        if any(keyword in command or keyword in description for keyword in ["memory", "ram", "mem"]):
            mem_value = self._extract_percentage_value(output, ["memory", "mem", "ram"])
            if mem_value is not None:
                metrics["memory"] = mem_value
        
        # Disk metrics
        if any(keyword in command or keyword in description for keyword in ["disk", "storage", "space", "usage"]):
            disk_value = self._extract_percentage_value(output, ["disk", "storage", "space", "usage"])
            if disk_value is not None:
                metrics["disk"] = disk_value
        
        # Network metrics
        if any(keyword in command or keyword in description for keyword in ["network", "bandwidth", "traffic"]):
            network_value = self._extract_percentage_value(output, ["network", "bandwidth", "traffic"])
            if network_value is not None:
                metrics["network"] = network_value
        
        return metrics
    
    def _extract_percentage_value(self, output: str, keywords: List[str]) -> Optional[float]:
        """
        Extract percentage value from output
        
        Args:
            output: Command output
            keywords: Keywords to look for
            
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
    
    def _is_ambiguous_output(self, output: str) -> bool:
        """
        Check if output is ambiguous/unclear
        
        Args:
            output: Command output
            
        Returns:
            True if output is ambiguous
        """
        output_lower = output.lower()
        
        # Check for error indicators
        error_indicators = [
            "error", "failed", "not found", "cannot", "unable",
            "exception", "traceback", "undefined", "null", "none"
        ]
        
        if any(indicator in output_lower for indicator in error_indicators):
            return True
        
        # Check if output is too short or empty
        if len(output.strip()) < 5:
            return True
        
        # Check if output doesn't contain numbers (likely not a metric)
        if not re.search(r'\d', output):
            return True
        
        return False
    
    async def _compare_metrics_to_ticket(
        self,
        ticket: Ticket,
        metrics: Dict[str, float],
        runbook: Optional[Runbook] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Compare extracted metrics to ticket description and thresholds
        
        Args:
            ticket: Ticket object
            metrics: Extracted metrics dictionary
            runbook: Optional runbook object
            db: Optional database session for loading thresholds
            
        Returns:
            Comparison result
        """
        ticket_desc = (ticket.description or "").lower()
        ticket_title = (ticket.title or "").lower()
        combined_text = f"{ticket_title} {ticket_desc}"
        
        false_positive_indicators = []
        true_positive_indicators = []
        confidence = 0.0
        
        # Check each metric
        for metric_name, value in metrics.items():
            # Get threshold for this metric
            thresholds = self.threshold_service.get_thresholds(
                metric=metric_name,
                environment=ticket.environment or "prod",  # Default to prod if not set
                service=ticket.service,
                tenant_id=ticket.tenant_id,
                runbook=runbook,
                db=db
            )
            
            threshold_source = thresholds.get("source", "default")
            warning_threshold = thresholds.get("warning", 80.0)
            critical_threshold = thresholds.get("critical", 90.0)
            
            logger.info(
                f"Using thresholds for {metric_name} in {ticket.environment or 'prod'}: "
                f"warning={warning_threshold}%, critical={critical_threshold}% (source: {threshold_source})"
            )
            
            # Check if ticket mentions this metric as high/problematic
            metric_keywords = {
                "cpu": ["cpu", "processor", "high cpu", "cpu usage"],
                "memory": ["memory", "ram", "mem", "high memory", "memory usage"],
                "disk": ["disk", "storage", "space", "disk usage", "disk full"],
                "network": ["network", "bandwidth", "traffic", "network usage"]
            }
            
            mentions_metric = any(
                keyword in combined_text
                for keyword in metric_keywords.get(metric_name, [])
            )
            
            # Enhanced comparison logic: Check metric value against thresholds regardless of ticket mention
            # This handles cases where ticket doesn't explicitly mention the metric but metric is high
            if value < warning_threshold:
                # Value is below warning threshold - likely FALSE POSITIVE if ticket claims issue
                if mentions_metric:
                    false_positive_indicators.append(
                        f"{metric_name} is {value:.1f}% (below warning threshold {warning_threshold}%), "
                        f"but ticket reports it as high"
                    )
                    confidence = max(confidence, 0.9)  # High confidence for false positive
                else:
                    # Metric is low and ticket doesn't mention it - neutral, but log it
                    logger.debug(f"{metric_name} is {value:.1f}% (normal), ticket doesn't mention it")
            elif value >= critical_threshold:
                # Value is above critical threshold - definitely TRUE POSITIVE
                true_positive_indicators.append(
                    f"{metric_name} is {value:.1f}% (above critical threshold {critical_threshold}%)"
                )
                confidence = max(confidence, 0.9)  # High confidence for true positive
            elif value >= warning_threshold:
                # Value is in warning range - TRUE POSITIVE (but medium confidence)
                true_positive_indicators.append(
                    f"{metric_name} is {value:.1f}% (above warning threshold {warning_threshold}%)"
                )
                confidence = max(confidence, 0.7)  # Medium confidence
            else:
                # This shouldn't happen, but handle it
                logger.warning(f"Unexpected metric value {value} for {metric_name}")
        
        # Determine result
        if false_positive_indicators and not true_positive_indicators:
            is_false_positive = True
            reasoning = f"False positive detected: {', '.join(false_positive_indicators)}"
            confidence = min(confidence, 0.9)  # Cap at 0.9 for false positives
            logger.info(f"False positive detected with confidence {confidence:.2f}: {reasoning}")
        elif true_positive_indicators and not false_positive_indicators:
            is_false_positive = False
            reasoning = f"True positive confirmed: {', '.join(true_positive_indicators)}"
            confidence = min(confidence, 0.9)
            logger.info(f"True positive confirmed with confidence {confidence:.2f}: {reasoning}")
        elif false_positive_indicators and true_positive_indicators:
            # Mixed signals - uncertain, but prioritize true positive (safer to proceed)
            is_false_positive = False
            reasoning = f"Mixed indicators: {', '.join(false_positive_indicators)} vs {', '.join(true_positive_indicators)}. Proceeding with caution."
            confidence = 0.5
            logger.warning(f"Mixed indicators detected, proceeding with caution: {reasoning}")
        else:
            # No clear indicators - if we have metrics but no indicators, check if any metric is high
            if extracted_metrics:
                # Check if any metric is above warning threshold (even if ticket doesn't mention it)
                high_metrics = []
                for metric_name, value in extracted_metrics.items():
                    thresholds = self.threshold_service.get_thresholds(
                        metric=metric_name,
                        environment=ticket.environment or "prod",
                        service=ticket.service,
                        tenant_id=ticket.tenant_id,
                        runbook=runbook,
                        db=db
                    )
                    warning_threshold = thresholds.get("warning", 80.0)
                    if value >= warning_threshold:
                        high_metrics.append(f"{metric_name} is {value:.1f}%")
                
                if high_metrics:
                    is_false_positive = False
                    reasoning = f"Metrics indicate potential issue: {', '.join(high_metrics)}. Proceeding with troubleshooting."
                    confidence = 0.6
                    logger.info(f"High metrics detected without explicit ticket mention: {reasoning}")
                else:
                    is_false_positive = False
                    reasoning = "Could not determine false positive from precheck outputs. All metrics are within normal range."
                    confidence = 0.3
                    logger.info(f"No clear indicators, all metrics normal: {reasoning}")
            else:
                # No metrics extracted at all
                is_false_positive = False
                reasoning = "Could not extract metrics from precheck outputs. Proceeding with execution."
                confidence = 0.3
                logger.warning(f"No metrics extracted from precheck outputs: {reasoning}")
        
        return {
            "is_false_positive": is_false_positive,
            "confidence": confidence,
            "reasoning": reasoning
        }


# Global instance
_precheck_analysis_service: Optional[PrecheckAnalysisService] = None


def get_precheck_analysis_service() -> PrecheckAnalysisService:
    """Get or create precheck analysis service instance"""
    global _precheck_analysis_service
    if _precheck_analysis_service is None:
        _precheck_analysis_service = PrecheckAnalysisService()
    return _precheck_analysis_service

