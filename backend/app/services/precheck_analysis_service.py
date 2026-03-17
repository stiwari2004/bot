"""
Precheck Analysis Service - Analyze precheck outputs to determine false positives
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.runbook import Runbook
from app.services.threshold_service import get_threshold_service
from app.services.precheck_metrics_mixin import PrecheckMetricsMixin

logger = get_logger(__name__)


class PrecheckAnalysisService(PrecheckMetricsMixin):
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
        """Analyze precheck step outputs to determine if ticket is false positive."""
        try:
            logger.info(f"Starting precheck analysis for ticket {ticket.id}, session {session.id}")

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
        """Analyze precheck outputs to determine false positive."""
        extracted_metrics = {}
        ambiguous_outputs = []

        logger.info(f"Extracting metrics from {len(precheck_outputs)} precheck outputs")

        for precheck in precheck_outputs:
            output = precheck.get("output", "")
            command = precheck.get("command", "").lower()
            description = precheck.get("description", "").lower()
            step_number = precheck.get("step_number", 0)

            metrics = self._extract_metrics_from_output(output, command, description)

            if metrics:
                logger.info(f"Extracted metrics from precheck step {step_number}: {metrics}")
                extracted_metrics.update(metrics)
            else:
                if self._is_ambiguous_output(output):
                    logger.warning(f"Ambiguous output detected in precheck step {step_number}")
                    ambiguous_outputs.append(step_number)
                else:
                    logger.debug(f"No metrics extracted from precheck step {step_number}, but output is not ambiguous")

        if ambiguous_outputs:
            return {
                "is_false_positive": False,
                "confidence": 0.0,
                "reasoning": f"Ambiguous precheck outputs at steps: {ambiguous_outputs}",
                "analysis_status": "ambiguous",
                "metrics": extracted_metrics
            }

        if not extracted_metrics:
            return {
                "is_false_positive": False,
                "confidence": 0.5,
                "reasoning": "Could not extract metrics from precheck outputs, proceeding with execution",
                "analysis_status": "success",
                "metrics": {}
            }

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


# Global instance
_precheck_analysis_service: Optional[PrecheckAnalysisService] = None


def get_precheck_analysis_service() -> PrecheckAnalysisService:
    """Get or create precheck analysis service instance"""
    global _precheck_analysis_service
    if _precheck_analysis_service is None:
        _precheck_analysis_service = PrecheckAnalysisService()
    return _precheck_analysis_service
