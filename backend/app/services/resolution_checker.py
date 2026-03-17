"""
Resolution Checker — metric extraction and precheck/postcheck comparison
"""
import re
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionStep

logger = get_logger(__name__)


class ResolutionChecker:
    """Compares precheck/postcheck metrics to determine if an issue is resolved"""

    def __init__(self, threshold_service):
        self.threshold_service = threshold_service

    def compare_precheck_postcheck(
        self,
        db: Session,
        ticket_id: int,
        prechecks: List[ExecutionStep],
        postchecks: List[ExecutionStep],
    ) -> Optional[Dict[str, Any]]:
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return None

            precheck_metrics: Dict[str, float] = {}
            for precheck in prechecks:
                if precheck.completed and precheck.success and precheck.output:
                    precheck_metrics.update(self.extract_metrics_from_output(precheck.output, precheck.command or ""))

            postcheck_metrics: Dict[str, float] = {}
            for postcheck in postchecks:
                if postcheck.completed and postcheck.success and postcheck.output:
                    postcheck_metrics.update(self.extract_metrics_from_output(postcheck.output, postcheck.command or ""))

            if not precheck_metrics or not postcheck_metrics:
                return None

            improvements, regressions, unchanged = [], [], []

            for metric_name in set(precheck_metrics) & set(postcheck_metrics):
                pre_value = precheck_metrics[metric_name]
                post_value = postcheck_metrics[metric_name]

                thresholds = self.threshold_service.get_thresholds(
                    metric=metric_name,
                    environment=ticket.environment,
                    service=ticket.service,
                    tenant_id=ticket.tenant_id,
                )
                warning_threshold = thresholds.get("warning", 80.0)

                if pre_value >= warning_threshold and post_value < warning_threshold:
                    improvements.append(f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (resolved)")
                elif pre_value < warning_threshold and post_value >= warning_threshold:
                    regressions.append(f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (worsened)")
                elif abs(pre_value - post_value) < 5.0:
                    unchanged.append(f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (unchanged)")
                elif post_value < pre_value:
                    improvements.append(f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (improved)")
                else:
                    regressions.append(f"{metric_name}: {pre_value:.1f}% → {post_value:.1f}% (worsened)")

            if improvements and not regressions:
                resolved, confidence = True, 0.9
                reasoning = f"Issue resolved: {', '.join(improvements)}"
            elif improvements and regressions:
                resolved, confidence = False, 0.6
                reasoning = f"Mixed results: {', '.join(improvements)} but {', '.join(regressions)}"
            elif regressions:
                resolved, confidence = False, 0.8
                reasoning = f"Issue not resolved: {', '.join(regressions)}"
            elif unchanged:
                resolved, confidence = False, 0.7
                reasoning = f"No significant change: {', '.join(unchanged)}"
            else:
                resolved, confidence = False, 0.5
                reasoning = "Could not determine resolution status from metrics"

            return {
                "resolved": resolved,
                "confidence": confidence,
                "reasoning": reasoning,
                "precheck_metrics": precheck_metrics,
                "postcheck_metrics": postcheck_metrics,
            }

        except Exception as e:
            logger.error(f"Error comparing precheck/postcheck: {e}", exc_info=True)
            return None

    def extract_metrics_from_output(self, output: str, command: str) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        command_lower = command.lower()

        keyword_map = {
            "cpu": ["cpu", "processor", "processor time"],
            "memory": ["memory", "ram", "mem"],
            "disk": ["disk", "storage", "space", "usage"],
            "network": ["network", "bandwidth", "traffic"],
        }

        for metric_name, keywords in keyword_map.items():
            if any(kw in command_lower for kw in keywords):
                value = self.extract_percentage_value(output)
                if value is not None:
                    metrics[metric_name] = value

        return metrics

    def extract_percentage_value(self, output: str) -> Optional[float]:
        patterns = [
            r"(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*percent",
            r":\s*(\d+\.?\d*)",
            r"=\s*(\d+\.?\d*)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[-1])
                    if 0 <= value <= 100:
                        return value
                    elif value > 100:
                        return value / 100.0 * 100 if value <= 1 else None
                except (ValueError, IndexError):
                    continue
        return None
