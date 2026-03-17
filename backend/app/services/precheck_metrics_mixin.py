"""
Mixin: metric extraction and comparison helpers for PrecheckAnalysisService
"""
import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.core.logging import get_logger

logger = get_logger(__name__)


class PrecheckMetricsMixin:
    """Metric extraction and comparison helpers for PrecheckAnalysisService."""

    def _extract_metrics_from_output(
        self,
        output: str,
        command: str,
        description: str
    ) -> Dict[str, float]:
        """Extract metric values from command output."""
        metrics = {}

        if any(keyword in command or keyword in description for keyword in ["cpu", "processor", "processor time"]):
            cpu_value = self._extract_percentage_value(output, ["cpu", "processor"])
            if cpu_value is not None:
                metrics["cpu"] = cpu_value
                logger.info(f"✅ Extracted CPU value: {cpu_value}% from output (length: {len(output)} chars)")
            else:
                logger.warning(f"❌ Failed to extract CPU value from output. Output preview: {output[:200]}")

        if any(keyword in command or keyword in description for keyword in ["memory", "ram", "mem"]):
            mem_value = self._extract_percentage_value(output, ["memory", "mem", "ram"])
            if mem_value is not None:
                metrics["memory"] = mem_value

        if any(keyword in command or keyword in description for keyword in ["disk", "storage", "space", "usage"]):
            disk_value = self._extract_percentage_value(output, ["disk", "storage", "space", "usage"])
            if disk_value is not None:
                metrics["disk"] = disk_value

        if any(keyword in command or keyword in description for keyword in ["network", "bandwidth", "traffic"]):
            network_value = self._extract_percentage_value(output, ["network", "bandwidth", "traffic"])
            if network_value is not None:
                metrics["network"] = network_value

        return metrics

    def _extract_percentage_value(self, output: str, keywords: List[str]) -> Optional[float]:
        """Extract percentage value from output."""
        patterns = [
            (r'(?:processor|processor\s+time|cpu|memory|disk|network).*?:\s*(\d+\.?\d*)', True),
            (r'(\d+\.?\d*)\s*%', True),
            (r'(\d+\.?\d*)\s*percent', True),
            (r'(?<!:\d{2})\s*:\s*(\d+\.?\d*)(?!\s*[AP]M)', False),
            (r'=\s*(\d+\.?\d*)', True),
        ]

        for pattern, use_last in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    value_str = matches[-1] if use_last else matches[-1]
                    value = float(value_str)
                    if 0 <= value <= 100:
                        return value
                    elif 0 < value <= 1:
                        return value * 100
                    elif value > 100 and value <= 10000:
                        return value / 100.0
                    else:
                        logger.debug(f"Extracted value {value} is out of expected range (0-100), skipping")
                        continue
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing value from matches {matches}: {e}")
                    continue

        all_numbers = re.findall(r'\b(\d+\.?\d*)\b', output)
        if all_numbers:
            for num_str in reversed(all_numbers):
                try:
                    num = float(num_str)
                    if num > 1000 and num < 2100:
                        continue
                    if num > 0 and num <= 100:
                        logger.debug(f"Fallback: extracted value {num} from output")
                        return num
                except ValueError:
                    continue

        return None

    def _is_ambiguous_output(self, output: str) -> bool:
        """Check if output is ambiguous/unclear."""
        output_lower = output.lower()

        error_indicators = [
            "error", "failed", "not found", "cannot", "unable",
            "exception", "traceback", "undefined", "null", "none"
        ]

        if any(indicator in output_lower for indicator in error_indicators):
            return True
        if len(output.strip()) < 5:
            return True
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
        """Compare extracted metrics to ticket description and thresholds."""
        ticket_desc = (ticket.description or "").lower()
        ticket_title = (ticket.title or "").lower()
        combined_text = f"{ticket_title} {ticket_desc}"

        false_positive_indicators = []
        true_positive_indicators = []
        confidence = 0.0

        for metric_name, value in metrics.items():
            thresholds = self.threshold_service.get_thresholds(
                metric=metric_name,
                environment=ticket.environment or "prod",
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

            if value < warning_threshold:
                if mentions_metric:
                    false_positive_indicators.append(
                        f"{metric_name} is {value:.1f}% (below warning threshold {warning_threshold}%), "
                        f"but ticket reports it as high"
                    )
                    confidence = max(confidence, 0.9)
                else:
                    logger.debug(f"{metric_name} is {value:.1f}% (normal), ticket doesn't mention it")
            elif value >= critical_threshold:
                true_positive_indicators.append(
                    f"{metric_name} is {value:.1f}% (above critical threshold {critical_threshold}%)"
                )
                confidence = max(confidence, 0.9)
            elif value >= warning_threshold:
                true_positive_indicators.append(
                    f"{metric_name} is {value:.1f}% (above warning threshold {warning_threshold}%)"
                )
                confidence = max(confidence, 0.7)
            else:
                logger.warning(f"Unexpected metric value {value} for {metric_name}")

        if false_positive_indicators and not true_positive_indicators:
            is_false_positive = True
            reasoning = f"False positive detected: {', '.join(false_positive_indicators)}"
            confidence = min(confidence, 0.9)
            logger.info(f"False positive detected with confidence {confidence:.2f}: {reasoning}")
        elif true_positive_indicators and not false_positive_indicators:
            is_false_positive = False
            reasoning = f"True positive confirmed: {', '.join(true_positive_indicators)}"
            confidence = min(confidence, 0.9)
            logger.info(f"True positive confirmed with confidence {confidence:.2f}: {reasoning}")
        elif false_positive_indicators and true_positive_indicators:
            is_false_positive = False
            reasoning = f"Mixed indicators: {', '.join(false_positive_indicators)} vs {', '.join(true_positive_indicators)}. Proceeding with caution."
            confidence = 0.5
            logger.warning(f"Mixed indicators detected, proceeding with caution: {reasoning}")
        else:
            if extracted_metrics:
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
                is_false_positive = False
                reasoning = "Could not extract metrics from precheck outputs. Proceeding with execution."
                confidence = 0.3
                logger.warning(f"No metrics extracted from precheck outputs: {reasoning}")

        return {
            "is_false_positive": is_false_positive,
            "confidence": confidence,
            "reasoning": reasoning
        }
